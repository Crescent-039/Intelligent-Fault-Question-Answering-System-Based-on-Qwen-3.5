import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
app = FastAPI()
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("连接成功")
    try:
        # 初始化任务开始
        await websocket.send_text("你好，Qt前端！我是 Python 后端。")
        # 循环任务开始
        while True:
            data = await websocket.receive_text()
            print(f"收到前端的消息: {data}")

    except WebSocketDisconnect:
        # 如果断开
        print("Qt 客户端已断开连接。")

if __name__ == "__main__":
    # 通过netstat -an查询 不可用端口
    uvicorn.run(app, host="127.0.0.1", port=11451)