import asyncio
import json
import time
from pathlib import Path
from threading import Thread, Event

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import sys
sys.path.append("..")
sys.path.append("../src")
# 按你的实际路径修改
# 假设你的 send 函数在 src/rag_chat_service.py
from src.Communication import RagChatService
from Communication import RagChatService

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

rag_service = RagChatService()


@app.on_event("startup")
async def startup_event():
    rag_service.init_rag_service()


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

    send_lock = asyncio.Lock()
    active_request_id = None
    active_stop_event = None
    active_chat_task = None

    async def send_json(message):
        async with send_lock:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))

    async def run_chat_stream(data, request_id: str, stop_event: Event):
        nonlocal active_request_id, active_stop_event, active_chat_task

        params = parse_chat_payload(data)

        messages = params["messages"]
        file_ids = params["file_ids"]
        rag_enabled = params["rag_enabled"]
        rag_top_k = params["rag_top_k"]
        temperature = params["temperature"]
        max_tokens = params["max_tokens"]
        enable_thinking = params["enable_thinking"]

        await send_json({
            "request_id": request_id,
            "type": "stream_start",
            "payload": {
                "created_at": int(time.time())
            }
        })

        completion_tokens = 0

        try:
            sync_generator = rag_service.send(
                messages=messages,
                file_ids=file_ids,
                rag_top_k=rag_top_k,
                tem=temperature,
                max_tokens=max_tokens,
                thinking=enable_thinking,
                rag_enabled=rag_enabled,
                stop_event=stop_event
            )

            async for delta in async_wrap_sync_generator(sync_generator):
                if stop_event.is_set():
                    break
                if not delta:
                    continue

                completion_tokens += len(delta)

                await send_json({
                    "request_id": request_id,
                    "type": "stream_chunk",
                    "payload": {
                        "delta": delta
                    }
                })

            finish_reason = "cancelled" if stop_event.is_set() else "stop"
            await send_json({
                "request_id": request_id,
                "type": "stream_end",
                "payload": {
                    "finish_reason": finish_reason,
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": completion_tokens,
                        "total_tokens": completion_tokens,
                    }
                }
            })

        except Exception as e:
            print("模型生成失败:", e)

            await send_json({
                "request_id": request_id,
                "type": "error",
                "payload": {
                    "code": "MODEL_GENERATION_ERROR",
                    "message": str(e)
                }
            })

            await send_json({
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
            })

        finally:
            stop_event.set()
            if active_request_id == request_id:
                active_request_id = None
                active_stop_event = None
                active_chat_task = None

    try:
        while True:
            raw = await websocket.receive_text()
            print(f"收到前端的消息: {raw}")

            data = json.loads(raw)

            request_id = data["request_id"]
            msg_type = data["type"]

            if msg_type == "ping":
                await send_json({
                    "request_id": request_id,
                    "type": "pong",
                    "payload": {}
                })
                continue

            if msg_type == "cancel":
                if request_id == active_request_id and active_stop_event is not None:
                    print(f"收到停止消息: {msg_type}")
                    active_stop_event.set()
                else:
                    await send_json({
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
                    })
                continue

            if msg_type == "citation_detail":
                chunk_uid = data.get("payload", {}).get("chunk_uid")
                result = rag_service.get_citation_details(chunk_uid)
                if result is None:
                    await send_json({
                        "request_id": request_id,
                        "type": "error",
                        "payload": {
                            "code": "CITATION_NOT_FOUND",
                            "message": f"未找到 chunk_uid={chunk_uid} 对应的测试引用内容"
                        }
                    })
                else:
                    await send_json({
                        "request_id": request_id,
                        "type": "citation_detail_result",
                        "payload": {
                            "chunk_uid": chunk_uid,
                            "source": result.get("file_name","没找到source或者source不存在"),
                            "doc_id": result.get("file_id","没找到doc_id或者doc_id不存在"),
                            "text": result.get("text","没找到text或者text不存在")
                        }
                    })
                continue

            if msg_type == "chat":
                if active_chat_task is not None and not active_chat_task.done():
                    await send_json({
                        "request_id": request_id,
                        "type": "error",
                        "payload": {
                            "code": "CHAT_IN_PROGRESS",
                            "message": "当前已有对话正在生成"
                        }
                    })
                    continue

                active_request_id = request_id
                active_stop_event = Event()
                active_chat_task = asyncio.create_task(
                    run_chat_stream(data, request_id, active_stop_event)
                )

                continue

            # 其他消息类型暂时先不报错，预留给文件上传等功能
            await send_json({
                "request_id": request_id,
                "type": "ack",
                "payload": {
                    "message": f"已收到消息类型: {msg_type}，当前暂未处理。"
                }
            })
            continue

    except WebSocketDisconnect:
        print("Web 客户端已断开连接。")
        if active_stop_event is not None:
            active_stop_event.set()
        if active_chat_task is not None:
            active_chat_task.cancel()


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=SERVER_CONFIG["host"],
        port=SERVER_CONFIG["port"],
    )
