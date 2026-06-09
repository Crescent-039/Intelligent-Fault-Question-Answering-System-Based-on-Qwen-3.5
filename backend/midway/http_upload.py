import os
import uuid
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Lock, Thread
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from Communication import RagChatService

app = FastAPI()

server = RagChatService()

# 解决跨域问题（开发环境必备）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 生产环境建议替换为前端实际域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED_DIR = os.path.join(CURRENT_DIR, "uploads", "shared")
os.makedirs(SHARED_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {"txt", "md", "pdf", "docx", "csv", "xlsx", "xls", "html", "htm", "pptx","ppt"}

FILE_RECORDS = {}
FILE_RECORDS_LOCK = Lock()
CHINA_TZ = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(CHINA_TZ).isoformat(timespec="seconds")


def build_file_record(final_filename: str, file_type: str, index_status: str = "downloaded", message: str = "文件下载完成"):
    return {
        "file_id": final_filename,
        "filename": final_filename,
        "file_type": file_type,
        "path": f"/uploads/shared/{final_filename}",
        "index_status": index_status,
        "message": message,
        "uploaded_at": now_iso(),
    }


def update_file_record(file_id: str, **fields):
    with FILE_RECORDS_LOCK:
        record = FILE_RECORDS.get(file_id)
        if not record:
            return
        record.update(fields)


def process_uploaded_file(file_id: str, file_path: str):
    update_file_record(file_id, index_status="preprocessing", message="正在预处理文档")
    try:
        server.add_path_to_index(str(file_path))
        update_file_record(file_id, index_status="done", message="文档预处理完成")
    except Exception as e:
        update_file_record(file_id, index_status="failed", message=f"文档预处理失败：{str(e)}")


def get_or_create_file_record_from_disk(path: Path):
    if not path.is_file():
        return None

    ext_lower = path.suffix.lower().lstrip(".")
    if ext_lower not in ALLOWED_EXTENSIONS:
        return None

    file_id = path.name
    stat = path.stat()

    with FILE_RECORDS_LOCK:
        existing = FILE_RECORDS.get(file_id)
        if existing:
            return dict(existing)

    uploaded_at = datetime.fromtimestamp(stat.st_mtime, CHINA_TZ).isoformat(timespec="seconds")
    return {
        "file_id": file_id,
        "filename": file_id,
        "file_type": ext_lower,
        "path": f"/uploads/shared/{file_id}",
        "index_status": "done",
        "message": "文件已存在",
        "uploaded_at": uploaded_at,
    }

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...), 
    user_id: str = Form(...)
):
    original_filename = file.filename
    base_name, ext = os.path.splitext(original_filename)
    ext_with_dot = ext.lower()
    ext_lower = ext_with_dot.lstrip(".")
    
    if ext_lower not in ALLOWED_EXTENSIONS:
        # 返回失败响应
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": "不受支持的文件格式。"
            }
        )
    # 3. 处理重名覆盖问题 (类似 Windows 的自动编号)
    final_filename = original_filename
    file_path = os.path.join(SHARED_DIR, final_filename)
    
    counter = 1
    # 如果文件已存在，则自动加上 (1), (2)...
    while os.path.exists(file_path):
        final_filename = f"{base_name}({counter}){ext_with_dot}"
        file_path = os.path.join(SHARED_DIR, final_filename)
        counter += 1
    
    # 4. 保存文件到共享目录
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
         return JSONResponse(status_code=500, content={"status": "error", "message": "文件保存失败"})
    finally:
        file.file.close()

    record = build_file_record(final_filename, ext_lower)
    with FILE_RECORDS_LOCK:
        FILE_RECORDS[final_filename] = record

    Thread(target=process_uploaded_file, args=(final_filename, file_path), daemon=True).start()
        
    # 5. 返回成功响应
    # 因为没有 UUID 了，你可以把 final_filename 当作 file_id 来返回前端
    return {
        "status": "success",
        "file_id": final_filename, 
        "filename": final_filename,
        "file_type": ext_lower,
        "path": f"/uploads/shared/{final_filename}", 
        "index_status": record["index_status"],
        "message": record["message"],
        "uploaded_at": record["uploaded_at"],
    }



@app.get("/api/file/{file_id}/status")
async def get_file_status(file_id: str):
    path = Path(SHARED_DIR) / file_id
    record = get_or_create_file_record_from_disk(path)
    if not record:
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "code": "FILE_NOT_FOUND",
                "message": "文件不存在。",
            }
        )

    return record


@app.get("/api/files")
async def list_files(user_id: str):
    files = []
    for path in sorted(Path(SHARED_DIR).iterdir(), key=lambda item: item.name.lower()):
        record = get_or_create_file_record_from_disk(path)
        if record:
            files.append(record)

    return {
        "status": "success",
        "user_id": user_id,
        "files": files,
    }


@app.delete("/api/file/{file_id}")
async def delete_file(file_id: str):
    # TODO: 删除接口暂未实现，后续按统一的文件管理方案接入。
    return JSONResponse(
        status_code=501,
        content={
            "status": "todo",
            "file_id": file_id,
            "message": "文件删除接口暂为占位实现。"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=11451)