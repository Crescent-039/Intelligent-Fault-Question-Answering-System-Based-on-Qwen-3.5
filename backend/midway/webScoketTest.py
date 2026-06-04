import asyncio
import json
import time
from pathlib import Path
from threading import Thread

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import sys
sys.path.append("..")
sys.path.append("../src")
# 按你的实际路径修改
# 假设你的 send 函数在 src/rag_chat_service.py
from src.Communication import send

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config.json"


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    return loaded


CONFIG = load_config()
SERVER_CONFIG = CONFIG["backend"]["server"]
FRONTEND_CONFIG = {
    "protocol": CONFIG["protocol"],
    "frontend": CONFIG["frontend"],
}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CONFIG["backend"]["cors"]["allow_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/config/frontend")
async def get_frontend_config():
    return FRONTEND_CONFIG


def parse_chat_payload(data):
    """
    从前端 WebSocket 消息中解析参数。
    """
    payload = data.get("payload", {})

    messages = payload.get("messages", [])
    file_ids = payload.get("file_ids", [])

    rag = payload.get("rag", {}) or {}
    rag_enabled = rag.get("enabled", True)
    rag_top_k = rag.get("top_k", 10)

    model_config = payload.get("model_config", {}) or {}
    temperature = model_config.get("temperature", 0.3)
    max_tokens = model_config.get("max_tokens", 2048)
    enable_thinking = model_config.get("enable_thinking", False)

    return {
        "messages": messages,
        "file_ids": file_ids,
        "rag_enabled": rag_enabled,
        "rag_top_k": rag_top_k,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "enable_thinking": enable_thinking,
    }


async def async_wrap_sync_generator(sync_generator):
    """
    把普通同步生成器包装成异步生成器。

    你的 send(...) 是同步 generator：
        for text in send(...):
            yield text

    但 WebSocket endpoint 是 async 函数。
    为了避免模型生成时阻塞事件循环，这里用线程 + asyncio.Queue 转一下。
    """
    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    sentinel = object()

    def worker():
        try:
            for item in sync_generator:
                loop.call_soon_threadsafe(queue.put_nowait, item)
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, e)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, sentinel)

    Thread(target=worker, daemon=True).start()

    while True:
        item = await queue.get()

        if item is sentinel:
            break

        if isinstance(item, Exception):
            raise item

        yield item


@app.websocket(SERVER_CONFIG.get("ws_path"))
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("连接成功")

    try:
        while True:
            raw = await websocket.receive_text()
            print(f"收到前端的消息: {raw}")

            data = json.loads(raw)

            request_id = data["request_id"]
            msg_type = data["type"]

            if msg_type == "ping":
                await websocket.send_text(json.dumps({
                    "request_id": request_id,
                    "type": "pong",
                    "payload": {}
                }, ensure_ascii=False))
                continue

            if msg_type == "cancel":
                await websocket.send_text(json.dumps({
                    "request_id": request_id,
                    "type": "stream_end",
                    "payload": {
                        "finish_reason": "cancelled",
                        "usage": {
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0,
                        },
                    }
                }, ensure_ascii=False))
                continue

            if msg_type != "chat":
                await websocket.send_text(json.dumps({
                    "request_id": request_id,
                    "type": "error",
                    "payload": {
                        "code": "INVALID_MESSAGE",
                        "message": f"不支持的消息类型: {msg_type}"
                    }
                }, ensure_ascii=False))
                continue

            # =========================
            # 1. 解析前端参数
            # =========================
            params = parse_chat_payload(data)

            messages = params["messages"]
            file_ids = params["file_ids"]
            rag_enabled = params["rag_enabled"]
            rag_top_k = params["rag_top_k"]
            temperature = params["temperature"]
            max_tokens = params["max_tokens"]
            enable_thinking = params["enable_thinking"]

            # =========================
            # 2. 通知前端：开始流式输出
            # =========================
            await websocket.send_text(json.dumps({
                "request_id": request_id,
                "type": "stream_start",
                "payload": {
                    "created_at": int(time.time())
                }
            }, ensure_ascii=False))

            completion_tokens = 0

            try:
                # =========================
                # 3. 调用本地模型 send(...)
                # =========================
                sync_generator = send(
                    messages=messages,
                    file_ids=file_ids,
                    rag_top_k=rag_top_k,
                    tem=temperature,
                    max_tokens=max_tokens,
                    thinking=enable_thinking,
                    rag_enabled=rag_enabled
                )

                # =========================
                # 4. 把模型输出逐段发给前端
                # =========================
                async for delta in async_wrap_sync_generator(sync_generator):
                    if not delta:
                        continue

                    completion_tokens += len(delta)

                    await websocket.send_text(json.dumps({
                        "request_id": request_id,
                        "type": "stream_chunk",
                        "payload": {
                            "delta": delta
                        }
                    }, ensure_ascii=False))

                # =========================
                # 5. 通知前端：正常结束
                # =========================
                await websocket.send_text(json.dumps({
                    "request_id": request_id,
                    "type": "stream_end",
                    "payload": {
                        "finish_reason": "stop",
                        "usage": {
                            "prompt_tokens": 0,
                            "completion_tokens": completion_tokens,
                            "total_tokens": completion_tokens,
                        }
                    }
                }, ensure_ascii=False))

            except Exception as e:
                print("模型生成失败:", e)

                await websocket.send_text(json.dumps({
                    "request_id": request_id,
                    "type": "error",
                    "payload": {
                        "code": "MODEL_GENERATION_ERROR",
                        "message": str(e)
                    }
                }, ensure_ascii=False))

                await websocket.send_text(json.dumps({
                    "request_id": request_id,
                    "type": "stream_end",
                    "payload": {
                        "finish_reason": "error",
                        "usage": {
                            "prompt_tokens": 0,
                            "completion_tokens": completion_tokens,
                            "total_tokens": completion_tokens,
                        }
                    }
                }, ensure_ascii=False))

    except WebSocketDisconnect:
        print("Web 客户端已断开连接。")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=SERVER_CONFIG["host"],
        port=SERVER_CONFIG["port"],
    )
