import asyncio
import json
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware


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

            await websocket.send_text(json.dumps({
                "request_id": request_id,
                "type": "stream_start",
                "payload": {
                    "created_at": int(time.time())
                }
            }, ensure_ascii=False))

            answer = "这是 Python 后端返回的测试流式文本。"
            for char in answer:
                await websocket.send_text(json.dumps({
                    "request_id": request_id,
                    "type": "stream_chunk",
                    "payload": {
                        "delta": char
                    }
                }, ensure_ascii=False))
                await asyncio.sleep(0.03)

            await websocket.send_text(json.dumps({
                "request_id": request_id,
                "type": "stream_end",
                "payload": {
                    "finish_reason": "stop",
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": len(answer),
                        "total_tokens": len(answer),
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