import os

import faiss

from config import FILES_MANIFEST_PATH, TOP_K
from utils import load_json
from embedding_model import EmbeddingModel
from llm_model import LLMModel


def load_index_manifest():
    if not os.path.exists(FILES_MANIFEST_PATH):
        return {
            "_meta": {
                "next_global_chunk_id": 0
            }
        }
    manifest = load_json(FILES_MANIFEST_PATH)
    if not isinstance(manifest, dict):
        raise ValueError("files_manifest.json 格式错误，应为对象字典")
    return manifest


def resolve_target_file_ids(file_ids, manifest):
    manifest_file_ids = [key for key in manifest.keys() if key != "_meta"]
    if not file_ids:
        return manifest_file_ids
    return [file_id for file_id in file_ids if file_id in manifest]


def retrieve_by_file_ids(query, embedder, file_ids=None, top_k=3):
    manifest = load_index_manifest()
    target_file_ids = resolve_target_file_ids(file_ids or [], manifest)
    if not target_file_ids:
        return []

    query_embedding = embedder.encode([query])
    all_results = []

    for file_id in target_file_ids:
        file_meta = manifest.get(file_id, {})
        chunks_path = file_meta.get("chunks_path")
        index_path = file_meta.get("index_path")
        if not chunks_path or not index_path:
            continue
        if not os.path.exists(chunks_path) or not os.path.exists(index_path):
            continue

        chunk_records = load_json(chunks_path)
        if not chunk_records:
            continue

        index = faiss.read_index(index_path)
        current_top_k = min(top_k, len(chunk_records))
        if current_top_k <= 0:
            continue

        scores, indices = index.search(query_embedding, current_top_k)
        for score, local_idx in zip(scores[0], indices[0]):
            if local_idx < 0 or local_idx >= len(chunk_records):
                continue
            chunk = chunk_records[local_idx]
            all_results.append({
                "score": float(score),
                "file_id": file_id,
                "global_id": chunk.get("id"),
                "local_chunk_id": chunk.get("local_chunk_id", int(local_idx)),
                "anchor": chunk.get("Anchor", []),
                "text": chunk.get("text", ""),
                "source": chunk.get("source", file_meta.get("file_path", "")),
                "file_name": os.path.basename(chunk.get("source", file_meta.get("file_path", "")))
            })

    all_results.sort(key=lambda item: item["score"], reverse=True)
    return all_results[:top_k]


def resolve_citation(chunk_uid: int):
    manifest = load_index_manifest()
    for file_id, file_meta in manifest.items():
        if file_id == "_meta":
            continue
        chunks_path = file_meta["chunks_path"]
        if not chunks_path or not os.path.exists(chunks_path):
            continue
        chunk_records = load_json(chunks_path)
        for i, chunk in enumerate(chunk_records):
            if chunk["id"] == chunk_uid:
                if i > 0:
                    last_text = chunk_records[i-1]["text"]
                else:
                    last_text = ""
                try:
                    next_text = chunk_records[i+1]["text"]
                except:
                    next_text = ""
                source = chunk["source"]

                last = chunk_clear(last_text, chunk["text"])
                current = chunk_clear(last, next_text)

                return {
                    "chunk_uid": chunk["id"],
                    "global_id": chunk["id"],
                    "anchor": chunk["Anchor"],
                    "file_id": chunk["file_id"],
                    "local_chunk_id": chunk["local_chunk_id"],
                    "file_name": os.path.basename(source),
                    "source": source,
                    "extension": chunk["extension"],
                    "text": current
                }
    return None

def chunk_clear(a, b):
    c=a+b
    for i in range(len(a) if len(a)<len(b) else len(b)):
        if a[-i-1:]!=b[:i+1]:
            pass
        else:
            c = a[:-i-1]+b
    return c

def build_context(results):
    context_parts = []
    for i, item in enumerate(results):
        source = item.get("source", "")
        score = item.get("score", 0.0)
        text = item.get("text", "")
        anchors = item.get("Anchor")
        if anchors is None:
            anchors = item.get("anchor", [])
        if isinstance(anchors, list):
            anchor_text = "[" + ", ".join(str(anchor) for anchor in anchors) + "]"
        else:
            anchor_text = f"[{anchors}]"
        context_parts.append(
            f"[片段{i + 1} | score={score:.4f} | source={source} | Anchor={anchor_text}]\n"
            f"{text}"
        )
    return "\n\n".join(context_parts)


def main():
    print("===== 加载本地分文件索引 =====")
    manifest = load_index_manifest()
    file_ids = resolve_target_file_ids([], manifest)
    print(f"已加载索引文件数: {len(file_ids)}")

    embedder = EmbeddingModel(device='cpu')
    llm = LLMModel()

    print("===== 开始问答 =====")
    while True:
        query = input("\n请输入问题（输入 exit 退出）：").strip()
        if query.lower() in ["exit", "quit"]:
            print("退出问答。")
            break

        results = retrieve_by_file_ids(query, embedder, file_ids=file_ids, top_k=TOP_K)

        print("\n检索结果：")
        for item in results:
            print(
                f"\n[file_id={item['file_id']}, global_id={item['global_id']}, "
                f"local_chunk_id={item['local_chunk_id']}, score={item['score']:.4f}]"
            )
            print(item["text"])

        # 5. 拼接上下文
        context = build_context(results)

        # 6. LLM 流式回答
        print("\n正在生成答案...\n")
        print("模型回答：", end="", flush=True)
        for new_text in llm.stream_chat(query, context, enable_thinking=True):
            print(new_text, end="", flush=True)
        print()


if __name__ == "__main__":
    main()
# --coding:utf-8--
