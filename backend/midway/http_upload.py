import os
import uuid
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Thread
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil

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
TMP_DIR = os.path.join(CURRENT_DIR, "uploads", "tmp")
os.makedirs(SHARED_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {"txt", "md", "pdf", "docx", "csv", "xlsx", "xls", "html", "htm", "pptx","ppt"}

CHINA_TZ = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(CHINA_TZ).isoformat(timespec="seconds")


def build_file_record(final_filename: str, file_type: str, index_status: str = "downloaded", message: str = "文件下载完成"):
    return {
        "file_id": final_filename,
        "filename": final_filename,
        "file_type": file_type,
        "path": f"/uploads/tmp/{final_filename}",
        "index_status": index_status,
        "message": message,
        "uploaded_at": now_iso(),
    }


def process_uploaded_file(file_id: str, tmp_path: str):
    try:
        server.add_path_to_index(str(tmp_path))
        shutil.move(tmp_path, SHARED_DIR)
    except Exception as e:
        print(f"文档预处理失败：{file_id}: {str(e)}")


def get_or_create_file_record_from_disk(path: Path):
    if not path.is_file():
        return None

    ext_lower = path.suffix.lower().lstrip(".")
    if ext_lower not in ALLOWED_EXTENSIONS:
        return None

    file_id = path.name
    stat = path.stat()

    uploaded_at = datetime.fromtimestamp(stat.st_mtime, CHINA_TZ).isoformat(timespec="seconds")
    in_shared = path.parent == Path(SHARED_DIR)
    default_status = "done" if in_shared else "downloaded"
    default_message = "文件已完成预处理" if in_shared else "文件已上传，等待预处理"

    return {
        "file_id": file_id,
        "filename": file_id,
        "file_type": ext_lower,
        "path": f"/uploads/{'shared' if in_shared else 'tmp'}/{file_id}",
        "index_status": default_status,
        "message": default_message,
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
    tmp_path = os.path.join(TMP_DIR, final_filename)
    
    counter = 1
    # 如果文件已存在，则自动加上 (1), (2)...
    while os.path.exists(tmp_path):
        final_filename = f"{base_name}({counter}){ext_with_dot}"
        tmp_path = os.path.join(TMP_DIR, final_filename)
        counter += 1
    
    # 4. 保存文件到共享目录
    try:
        with open(tmp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
         return JSONResponse(status_code=500, content={"status": "error", "message": "文件保存失败"})
    finally:
        file.file.close()

    record = build_file_record(final_filename, ext_lower)

    Thread(target=process_uploaded_file, args=(final_filename, tmp_path), daemon=True).start()

    # 5. 返回成功响应
    # 因为没有 UUID 了，你可以把 final_filename 当作 file_id 来返回前端
    return {
        "status": "success",
        "file_id": final_filename, 
        "filename": final_filename,
        "file_type": ext_lower,
        "path": record["path"], 
        "index_status": record["index_status"],
        "message": record["message"],
        "uploaded_at": record["uploaded_at"],
    }



@app.get("/api/file/{file_id}/status")
async def get_file_status(file_id: str):
    record = get_or_create_file_record_from_disk(Path(SHARED_DIR) / file_id)
    if not record:
        record = get_or_create_file_record_from_disk(Path(TMP_DIR) / file_id)
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
    shared_names = set()
    for path in sorted(Path(SHARED_DIR).iterdir(), key=lambda item: item.name.lower()):
        record = get_or_create_file_record_from_disk(path)
        if record:
            shared_names.add(path.name)
            files.append(record)
    for path in sorted(Path(TMP_DIR).iterdir(), key=lambda item: item.name.lower()):
        if path.name in shared_names:
            continue
        record = get_or_create_file_record_from_disk(path)
        if record:
            files.append(record)

    return {
        "status": "success",
        "user_id": user_id,
        "files": files,
    }


@app.post("/api/file/{file_id}/retry-preprocess")
async def retry_preprocess(file_id: str):
    shared_path = Path(SHARED_DIR) / file_id
    if shared_path.is_file():
        return get_or_create_file_record_from_disk(shared_path)

    tmp_path = Path(TMP_DIR) / file_id
    record = get_or_create_file_record_from_disk(tmp_path)
    if not record:
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "code": "FILE_NOT_FOUND",
                "message": "文件不存在。",
            }
        )

    record["message"] = "文件已重新提交预处理"
    Thread(target=process_uploaded_file, args=(file_id, str(tmp_path)), daemon=True).start()
    return record


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