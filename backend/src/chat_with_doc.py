import faiss

from config import FAISS_INDEX_PATH, CHUNKS_PATH, TOP_K
from utils import load_json
from embedding_model import EmbeddingModel
from llm_model import LLMModel


def retrieve(query, embedder, index, chunk_records, top_k=3):
    query_embedding = embedder.encode([query])
    scores, indices = index.search(query_embedding, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(chunk_records):
            continue
        results.append({
            "score": float(score),
            "chunk_id": int(idx),
            "text": chunk_records[idx]["text"],
            "source": chunk_records[idx]["source"]
        })
    return results


def build_context(results):
    context_parts = []
    for i, item in enumerate(results):
        context_parts.append(
            f"[片段{i + 1} | score={item['score']:.4f} | source={item['source']}]\n{item['text']}"
        )
    return "\n\n".join(context_parts)


def main():
    print("===== 加载本地索引 =====")

    # 1. 加载 chunk 元数据
    chunk_records = load_json(CHUNKS_PATH)
    print(f"已加载 chunks: {len(chunk_records)}")

    # 2. 加载 FAISS 索引
    index = faiss.read_index(FAISS_INDEX_PATH)
    print("FAISS 索引加载完成")

    # 3. 加载模型
    embedder = EmbeddingModel(device='cpu')
    llm = LLMModel()

    print("===== 开始问答 =====")
    while True:
        query = input("\n请输入问题（输入 exit 退出）：").strip()
        if query.lower() in ["exit", "quit"]:
            print("退出问答。")
            break

        # 4. 检索
        results = retrieve(query, embedder, index, chunk_records, top_k=TOP_K)

        print("\n检索结果：")
        for item in results:
            print(f"\n[chunk_id={item['chunk_id']}, score={item['score']:.4f}]")
            print(item["text"])

        # 5. 拼接上下文
        context = build_context(results)

        # 6. LLM 回答
        print("\n正在生成答案...\n")
        answer = llm.chat(query, context)
        print("模型回答：")
        print(answer)


if __name__ == "__main__":
    main()
# --coding:utf-8--
