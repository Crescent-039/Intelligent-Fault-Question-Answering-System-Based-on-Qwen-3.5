import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Thread
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import sys
sys.path.append("..")
sys.path.append("../src")

CHINA_TZ = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(CHINA_TZ).isoformat(timespec="seconds")


class httpUpload:
    def __init__(self, app, server=None):
        self.app = app
        self.server = server
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.shared_dir = os.path.join(self.current_dir, "uploads", "shared")
        self.tmp_dir = os.path.join(self.current_dir, "uploads", "tmp")
        self.allowed_extensions = {"txt", "md", "pdf", "docx", "csv", "xlsx", "xls", "html", "htm", "pptx", "ppt"}

        os.makedirs(self.shared_dir, exist_ok=True)
        os.makedirs(self.tmp_dir, exist_ok=True)

    def register(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.app.add_api_route("/api/upload", self.upload_file, methods=["POST"])
        self.app.add_api_route("/api/file/{file_id}/status", self.get_file_status, methods=["GET"])
        self.app.add_api_route("/api/files", self.list_files, methods=["GET"])
        self.app.add_api_route("/api/file/{file_id}/retry-preprocess", self.retry_preprocess, methods=["POST"])
        self.app.add_api_route("/api/file/{file_id}", self.delete_file, methods=["DELETE"])

    def build_file_record(self, final_filename: str, file_type: str, index_status: str = "downloaded", message: str = "文件下载完成"):
        return {
            "file_id": final_filename,
            "filename": final_filename,
            "file_type": file_type,
            "path": f"/uploads/tmp/{final_filename}",
            "index_status": index_status,
            "message": message,
            "uploaded_at": now_iso(),
        }

    def process_uploaded_file(self, file_id: str, tmp_path: str):
        try:
            self.server.add_path_to_index(str(tmp_path))
            shutil.move(tmp_path, self.shared_dir)
        except Exception as e:
            print(f"文档预处理失败：{file_id}: {str(e)}")

    def get_or_create_file_record_from_disk(self, path: Path):
        if not path.is_file():
            return None

        ext_lower = path.suffix.lower().lstrip(".")
        if ext_lower not in self.allowed_extensions:
            return None

        file_id = path.name
        stat = path.stat()

        uploaded_at = datetime.fromtimestamp(stat.st_mtime, CHINA_TZ).isoformat(timespec="seconds")
        in_shared = path.parent == Path(self.shared_dir)
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

    async def upload_file(
        self,
        file: UploadFile = File(...),
        user_id: str = Form(...)
    ):
        original_filename = file.filename
        base_name, ext = os.path.splitext(original_filename)
        ext_with_dot = ext.lower()
        ext_lower = ext_with_dot.lstrip(".")

        if ext_lower not in self.allowed_extensions:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": "UNSUPPORTED_FILE_TYPE",
                    "message": "不受支持的文件格式。"
                }
            )

        final_filename = original_filename
        tmp_path = os.path.join(self.tmp_dir, final_filename)

        counter = 1
        while os.path.exists(tmp_path):
            final_filename = f"{base_name}({counter}){ext_with_dot}"
            tmp_path = os.path.join(self.tmp_dir, final_filename)
            counter += 1

        try:
            with open(tmp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": "文件保存失败"})
        finally:
            file.file.close()

        record = self.build_file_record(final_filename, ext_lower)

        Thread(target=self.process_uploaded_file, args=(final_filename, tmp_path), daemon=True).start()

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

    async def get_file_status(self, file_id: str):
        record = self.get_or_create_file_record_from_disk(Path(self.shared_dir) / file_id)
        if not record:
            record = self.get_or_create_file_record_from_disk(Path(self.tmp_dir) / file_id)
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

    async def list_files(self, user_id: str):
        files = []
        shared_names = set()
        for path in sorted(Path(self.shared_dir).iterdir(), key=lambda item: item.name.lower()):
            record = self.get_or_create_file_record_from_disk(path)
            if record:
                shared_names.add(path.name)
                files.append(record)
        for path in sorted(Path(self.tmp_dir).iterdir(), key=lambda item: item.name.lower()):
            if path.name in shared_names:
                continue
            record = self.get_or_create_file_record_from_disk(path)
            if record:
                files.append(record)

        return {
            "status": "success",
            "user_id": user_id,
            "files": files,
        }

    async def retry_preprocess(self, file_id: str):
        shared_path = Path(self.shared_dir) / file_id
        if shared_path.is_file():
            return self.get_or_create_file_record_from_disk(shared_path)

        tmp_path = Path(self.tmp_dir) / file_id
        record = self.get_or_create_file_record_from_disk(tmp_path)
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
        Thread(target=self.process_uploaded_file, args=(file_id, str(tmp_path)), daemon=True).start()
        return record

    async def delete_file(self, file_id: str):
        try:
            self.server.delete_file_from_index(file_id)
        except Exception as e:
            print(f"文件删除失败：{file_id}: {str(e)}")
            return {
                "status": "error",
                "file_id": file_id,
                "message": f"文件删除失败，发生了错误{str(e)}。"
            }

        return {
            "status": "success",
            "file_id": file_id,
            "message": "文件删除成功。"
        }
if __name__ == "__main__":
    import uvicorn
    app = FastAPI()
    upload_service = httpUpload(server=server, app=app)
    upload_service.register()
    uvicorn.run(app, host="127.0.0.1", port=11451)
