import faiss
from config import CHUNKS_PATH, FAISS_INDEX_PATH
from utils import load_json
from embedding_model import EmbeddingModel
from llm_model import LLMModel
from chat_with_doc import retrieve, build_context
import sys
sys.path.append("..")

# 全局加载，避免加载多次
chunk_records = load_json(CHUNKS_PATH)
index = faiss.read_index(FAISS_INDEX_PATH)
embedder = EmbeddingModel(device="cpu")
llm = LLMModel()


def get_last_user_message(messages):
    """
    从前端传来的完整 messages 中，取最后一个 user 的 content。
    """
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def filter_chunks_by_file_ids(chunk_record, file_ids):
    """
    根据 file_ids 过滤 chunks。
    要求 chunks.json 里有 file_id 字段。
    """
    if not file_ids:
        return chunk_record
    return [
        item for item in chunk_record
        if item.get("doc_id") in file_ids
    ]


def send(messages, file_ids=None, rag_top_k=10, tem=0.3, max_tokens=2048, thinking=True, rag_enabled=True):
    file_ids = file_ids or []
    query = get_last_user_message(messages)

    if not query:
        yield "用户暂时没有询问问题"
        return
    context = ""
    if rag_enabled:
        # 如果有 file_ids，先过滤 chunk_records
        # 如果你当前 chunks.json 里没有 file_id 字段，可以先注释掉这一行
        filtered_chunk_records = filter_chunks_by_file_ids(chunk_records, file_ids)
        # 如果没有过滤结果，就退回全部文档
        if not filtered_chunk_records:
            filtered_chunk_records = chunk_records
        results = retrieve(
            query=query,
            embedder=embedder,
            index=index,
            chunk_records=filtered_chunk_records,
            top_k=rag_top_k
        )
        context = build_context(results)
    # 流式输出
    for new_text in llm.stream_chat(
            query=query,
            context=context,
            temperature=tem,
            max_tokens=max_tokens,
            enable_thinking=thinking
    ):
        yield new_text


if __name__ == "__main__":

    # 假设前端传这些
    _messages = [
        {"role": "system", "content": "你是一个文档分析助手"},
        {"role": "user", "content": "帮我总结这份报告的核心内容"},
        {"role": "assistant", "content": "好的，以下是核心内容..."},
        {"role": "user", "content": "重点说一下第三章"}
    ]

    for text in send(
            messages=_messages,
            file_ids=["uuid-1", "uuid-2"],
            rag_top_k=5,
            tem=0.3,
            max_tokens=1024,
            thinking=False,
            rag_enabled=True
    ):
        print(text, end="", flush=True)
# --coding:utf-8--
