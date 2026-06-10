from embedding_model import EmbeddingModel
from llm_model import LLMModel
from chat_with_doc import retrieve_by_file_ids, build_context, resolve_citations
from build_index import Builder
import sys
from threading import Lock
sys.path.append("..")


class RagChatService:
    def __init__(self):
        self.embedder = None
        self.llm = None
        self.ready = False
        self.index_builder = None
        self.model_lock = Lock()
        self.init_rag_service()

    def init_rag_service(self, load_llm=True, warmup=True):
        if not load_llm:
            self.embedder = EmbeddingModel(device="cuda")
        else:
            self.embedder = EmbeddingModel(device="cpu")

        self.index_builder = Builder(embedder=self.embedder)
        if load_llm:
            self.llm = LLMModel(device="cuda")
            if warmup:
                self.warmup_llm()
        self.ready = True

    def add_file_to_index(self, file_id, file_path):
        return self.index_builder.build_file_index(
            file_id=file_id,
            file_path=file_path
        )

    def add_path_to_index(self, path):
        return self.index_builder.build_path_index(path)

    def warmup_llm(self):
        if self.llm is None:
            return
        print("[LLM] 正在 warmup...")
        for _ in self.llm.stream_chat(
                query="你好",
                context="",
                system_prompt="你是一个助手，请简短回答。",
                temperature=0.3,
                max_tokens=8,
                enable_thinking=False
        ):
            pass
        print("[LLM] warmup 完成")

    def get_last_user_message(self, messages):
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return ""

    def get_system_message(self, messages):
        for msg in messages:
            if msg.get("role") == "system":
                return msg.get("content", "")
        return ""

    def get_citation_details(self, chunk_uids):
        return resolve_citations(chunk_uids)

    def send(self, messages, file_ids=None, rag_top_k=10, tem=0.3, max_tokens=2048, thinking=True, rag_enabled=True, stop_event=None):
        file_ids = file_ids or []
        query = self.get_last_user_message(messages)
        system_prompt = self.get_system_message(messages)

        if not self.ready:
            raise RuntimeError("RAG 服务尚未初始化")
        if self.llm is None:
            raise RuntimeError("LLM 尚未初始化，无法执行问答")
        context = ""
        if rag_enabled:
            results = retrieve_by_file_ids(
                query=query,
                embedder=self.embedder,
                file_ids=file_ids,
                top_k=rag_top_k
            )
            context = build_context(results)
        # 流式输出
        for new_text in self.llm.stream_chat(
                query=query,
                context=context,
                system_prompt=system_prompt,
                temperature=tem,
                max_tokens=max_tokens,
                enable_thinking=thinking,
                stop_event=stop_event
        ):
            if stop_event is not None and stop_event.is_set():
                break
            yield new_text


if __name__ == "__main__":
    service = RagChatService()
    service.init_rag_service()

    # 假设前端传这些
    _messages = [
        {"role": "system", "content": "你是一个文档分析助手"},
        {"role": "user", "content": "帮我总结这份报告的核心内容"},
        {"role": "assistant", "content": "好的，以下是核心内容..."},
        {"role": "user", "content": "重点说一下第三章"}
    ]

    for text in service.send(
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
