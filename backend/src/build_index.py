import faiss

from config import (
    DOC_PATH,
    DATA_DIR,
    FAISS_INDEX_PATH,
    CHUNKS_PATH,
    CHUNK_SIZE,
    CHUNK_OVERLAP
)
from utils import ensure_dir, load_text, clean_text, chunk_text_by_sentences, save_json
from embedding_model import EmbeddingModel


def build_faiss_index(embeddings):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # 向量归一化后，用内积近似余弦相似度
    index.add(embeddings)
    return index


def main():
    print("===== 开始构建索引 =====")

    ensure_dir(DATA_DIR)

    # 1. 读取文档
    print(f"读取文档: {DOC_PATH}")
    raw_text = load_text(DOC_PATH)

    # 2. 清洗文本
    cleaned_text = clean_text(raw_text)

    # 3. 切块
    chunks = chunk_text_by_sentences(
        cleaned_text,
        chunk_size=CHUNK_SIZE,
        overlap_sentences=2
    )
    print(f"文本切分完成，共 {len(chunks)} 个 chunks")

    # 4. 构建 chunk 元数据
    chunk_records = []
    for idx, chunk in enumerate(chunks):
        chunk_records.append({
            "id": idx,
            "text": chunk,
            "source": DOC_PATH
        })

    # 5. 加载 embedding 模型
    embedder = EmbeddingModel()

    # 6. 生成向量
    texts = [item["text"] for item in chunk_records]
    print("开始生成 embeddings ...")
    embeddings = embedder.encode(texts)
    print("embeddings shape:", embeddings.shape)

    # 7. 建立 FAISS 索引
    print("开始构建 FAISS 索引 ...")
    index = build_faiss_index(embeddings)

    # 8. 保存 FAISS 索引
    faiss.write_index(index, FAISS_INDEX_PATH)
    print(f"FAISS 索引已保存: {FAISS_INDEX_PATH}")

    # 9. 保存 chunks 元数据
    save_json(chunk_records, CHUNKS_PATH)
    print(f"Chunks 信息已保存: {CHUNKS_PATH}")

    print("===== 索引构建完成 =====")


if __name__ == "__main__":
    main()
# --coding:utf-8--
