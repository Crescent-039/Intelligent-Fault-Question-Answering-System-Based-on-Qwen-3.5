import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.append(str(CURRENT_DIR))
sys.path.append(str(CURRENT_DIR.parent))
sys.path.append(str(CURRENT_DIR.parent / "src"))

from http_upload import httpUpload
from webSocket_chat import webSocketChat
from src.Communication import RagChatService


def create_app():
    app = FastAPI()
    server = RagChatService()

    chat_service = webSocketChat(server=server, app=app)
    chat_service.register()

    upload_service = httpUpload(server=server, app=app)
    upload_service.register()

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=11451,
    )
