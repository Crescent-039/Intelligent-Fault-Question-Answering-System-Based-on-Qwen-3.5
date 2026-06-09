import os
import uuid
import shutil
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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
        
    

    # 5. 返回成功响应
    # 因为没有 UUID 了，你可以把 final_filename 当作 file_id 来返回前端
    return {
        "status": "success",
        "file_id": final_filename, 
        "filename": final_filename,
        "file_type": ext_lower,
        "path": f"/uploads/shared/{final_filename}", 
        "index_status": "pending"
    }


@app.get("/api/file/{file_id}/status")
async def get_file_status(file_id: str):
    # TODO: 这里先保留为空白占位接口，后续由统一的文件管理/索引状态方案接管。
    return JSONResponse(
        status_code=501,
        content={
            "status": "todo",
            "file_id": file_id,
            "message": "文件索引状态查询接口暂为占位实现。"
        }
    )


@app.get("/api/files")
async def list_files(user_id: str):
    # TODO: 这里先保留为空白占位接口，后续由统一的文件管理方案接管。
    return JSONResponse(
        status_code=501,
        content={
            "status": "todo",
            "user_id": user_id,
            "message": "文件列表查询接口暂为占位实现。",
            "files": []
        }
    )


@app.delete("/api/file/{file_id}")
async def delete_file(file_id: str):
    # TODO: 这里先保留为空白占位接口，后续由统一的文件删除方案接管。
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