import faiss

from config import (
    DOCS_DIR,
    DATA_DIR,
    FAISS_INDEX_PATH,
    CHUNKS_PATH,
    CHUNK_SIZE,
    CHUNK_OVERLAP
)
from utils import ensure_dir, clean_text, chunk_text_by_sentences, save_json
from document_loader import load_all_documents
from embedding_model import EmbeddingModel


def build_faiss_index(embeddings):
    """
    构建 FAISS 索引。
    因为 embedding 已经做过 L2 normalize，
    所以 IndexFlatIP 的内积可以等价用于余弦相似度。
    """
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index


def build_chunk_records(documents):
    """
    将多个文档切成 chunks，并保留来源信息。
    """
    chunk_records = []
    global_chunk_id = 0

    for doc_id, doc in enumerate(documents):
        source = doc["source"]
        extension = doc["extension"]

        print(f"\n正在切分文档: {source}")

        cleaned_text = clean_text(doc["text"])

        chunks = chunk_text_by_sentences(
            cleaned_text,
            chunk_size=CHUNK_SIZE
        )

        print(f"该文档切分出 {len(chunks)} 个 chunks")

        for local_chunk_id, chunk in enumerate(chunks):
            chunk_records.append({
                "id": global_chunk_id,
                "doc_id": doc_id,
                "local_chunk_id": local_chunk_id,
                "text": chunk,
                "source": source,
                "extension": extension
            })

            global_chunk_id += 1

    return chunk_records


def main():
    print("===== 开始构建多文档索引 =====")

    ensure_dir(DATA_DIR)

    # 1. 加载 docs 目录下所有文档
    documents = load_all_documents(DOCS_DIR)

    if not documents:
        print("没有成功解析出任何文档，程序结束。")
        return

    print(f"\n成功解析文档数量: {len(documents)}")

    # 2. 文档切块
    chunk_records = build_chunk_records(documents)

    if not chunk_records:
        print("没有生成任何 chunk，程序结束。")
        return

    print(f"\n总 chunk 数量: {len(chunk_records)}")

    # 3. 加载 embedding 模型
    embedder = EmbeddingModel()

    # 4. 生成 embeddings
    texts = [item["text"] for item in chunk_records]

    print("\n开始生成 embeddings ...")
    embeddings = embedder.encode(texts)
    print("embeddings shape:", embeddings.shape)

    # 5. 建立 FAISS 索引
    print("\n开始构建 FAISS 索引 ...")
    index = build_faiss_index(embeddings)

    # 6. 保存 FAISS 索引
    faiss.write_index(index, FAISS_INDEX_PATH)
    print(f"FAISS 索引已保存: {FAISS_INDEX_PATH}")

    # 7. 保存 chunks 元数据
    save_json(chunk_records, CHUNKS_PATH)
    print(f"Chunks 信息已保存: {CHUNKS_PATH}")

    print("===== 多文档索引构建完成 =====")


if __name__ == "__main__":
    main()

