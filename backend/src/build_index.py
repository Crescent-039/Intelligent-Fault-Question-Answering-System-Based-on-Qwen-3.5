import faiss
import os
import uuid
from pathlib import Path

from config import (
    CHUNKS_DIR,
    INDEXES_DIR,
    FILES_MANIFEST_PATH,
    CHUNK_SIZE,
    CHUNK_OVERLAP
)
from utils import ensure_dir, clean_text, chunk_text_by_sentences, save_json, load_json
from document_loader import scan_documents, parse_document
from embedding_model import EmbeddingModel


class Builder:
    def __init__(self, embedder):
        self.embedder = embedder
        ensure_dir(CHUNKS_DIR)
        ensure_dir(INDEXES_DIR)

    def build_file_index(self, file_id, file_path):
        document = parse_document(file_path)
        cleaned_text = clean_text(document["text"])
        chunks = chunk_text_by_sentences(cleaned_text, chunk_size=CHUNK_SIZE, overlap_sentences=CHUNK_OVERLAP)
        if not chunks:
            raise ValueError("没有生成任何 chunk，程序结束。")
        manifest = self.load_manifest()
        start_global_id = manifest.get("_meta", {}).get("next_global_chunk_id", 0)
        chunk_records = []
        current_global_id = start_global_id
        for local_chunk_id, chunk in enumerate(chunks):
            chunk_records.append({
                "id": current_global_id,
                "Anchor": [f"r{current_global_id}"],
                "file_id": file_id,
                "local_chunk_id": local_chunk_id,
                "text": chunk,
                "source": file_path,
                "extension": document.get("extension", "")
            })
            current_global_id += 1
        texts = [item["text"] for item in chunk_records]
        embeddings = self.embedder.encode(texts)
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        chunks_path = self.get_chunks_path(file_id)
        index_path = self.get_index_path(file_id)
        save_json(chunk_records, chunks_path)
        faiss.write_index(index, index_path)
        self.update_manifest(
            manifest=manifest,
            file_id=file_id,
            file_path=file_path,
            chunks_path=chunks_path,
            index_path=index_path,
            chunk_count=len(chunk_records),
            start_global_id=start_global_id,
            end_global_id=current_global_id - 1,
            next_global_chunk_id=current_global_id
        )
        return {
            "file_id": file_id,
            "chunk_count": len(chunk_records),
            "start_global_id": start_global_id,
            "end_global_id": current_global_id - 1,
            "chunks_path": chunks_path,
            "index_path": index_path,
            "status": "indexed"
        }

    def build_path_index(self, path):
        path = Path(path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"路径不存在: {path}")
        if path.is_file():
            file_id = str(uuid.uuid4())
            return {
                "type": "file",
                "results": [
                    self.build_file_index(
                        file_id=file_id,
                        file_path=str(path)
                    )
                ]
            }
        if path.is_dir():
            file_paths = scan_documents(str(path), recursive=True)
            if not file_paths:
                raise ValueError(f"目录下没有支持的文档: {path}")
            results = []
            for file_path in file_paths:
                file_id = str(uuid.uuid4())
                result = self.build_file_index(
                    file_id=file_id,
                    file_path=file_path
                )
                results.append(result)
            return {
                "type": "directory",
                "file_count": len(results),
                "results": results
            }
        raise ValueError(f"不支持的路径类型: {path}")

    def delete_file_by_name(self, file_name):
        manifest = self.load_manifest()
        print(file_name)
        try:
            file_id, file_meta = self.find_file_by_name(manifest, file_name)
        except KeyError:
            print("未创建全局chunk文件")
            deleted_paths = [
                self.remove_path(Path("../midway") / "uploads" / "tmp" / file_name),
                self.remove_path(Path("../midway") / "uploads" / "shared" / file_name)
            ]
            return {
                "file_id": None,
                "file_name": file_name,
                "deleted_paths": [path for path in deleted_paths if path],
                "status": "deleted" if any(deleted_paths) else "not_found"
            }

        file_tmp_path = file_meta.get("file_path")
        file_tmp_parts = Path(file_tmp_path)
        parts = list(file_tmp_parts.parts)
        idx = parts.index("tmp")
        parts[idx] = "shared"
        file_shared_path = Path(*parts)
        print(file_shared_path)
        deleted_paths = [
            self.remove_path(file_tmp_path),
            self.remove_path(file_shared_path),
            self.remove_path(file_meta.get("chunks_path")),
            self.remove_path(file_meta.get("index_path"))
        ]

        return {
            "file_id": file_id,
            "file_name": file_name,
            "deleted_paths": [path for path in deleted_paths if path],
            "status": "deleted"
        }

    def find_file_by_name(self, manifest, file_name):
        for file_id, file_meta in manifest.items():
            if file_id == "_meta":
                continue
            if os.path.basename(file_meta.get("file_path", "")) == file_name:
                return file_id, file_meta
        raise KeyError(f"文件未建立索引: {file_name}")

    def remove_path(self, file_path):
        if not file_path:
            return None
        if os.path.exists(file_path):
            os.remove(file_path)
            return str(file_path)
        return None

    def get_chunks_path(self, file_id):
        return os.path.join(CHUNKS_DIR, f"{file_id}.json")

    def get_index_path(self, file_id):
        return os.path.join(INDEXES_DIR, f"{file_id}.index")

    def load_manifest(self):
        if os.path.exists(FILES_MANIFEST_PATH):
            return load_json(FILES_MANIFEST_PATH)
        return {
            "_meta": {
                "next_global_chunk_id": 0
            }
        }

    def update_manifest(
        self,
        manifest,
        file_id,
        file_path,
        chunks_path,
        index_path,
        chunk_count,
        start_global_id,
        end_global_id,
        next_global_chunk_id
    ):
        manifest[file_id] = {
            "file_id": file_id,
            "file_path": file_path,
            "chunks_path": chunks_path,
            "index_path": index_path,
            "chunk_count": chunk_count,
            "start_global_id": start_global_id,
            "end_global_id": end_global_id
        }
        manifest["_meta"] = {
            "next_global_chunk_id": next_global_chunk_id
        }
        save_json(manifest, FILES_MANIFEST_PATH)







