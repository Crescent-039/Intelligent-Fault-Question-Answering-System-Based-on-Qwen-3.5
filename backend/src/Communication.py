from embedding_model import EmbeddingModel
from llm_model import LLMModel
from chat_with_doc import retrieve_by_file_ids, build_context, resolve_citation, stream_chat_with_timing
from build_index import Builder
import sys
import torch
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
        self.embedder = EmbeddingModel(device="cuda")

        self.index_builder = Builder(embedder=self.embedder)
        if load_llm:
            self.llm = LLMModel(device="cuda")
            if warmup:
                self.warmup_llm()
                self.warmup_embedding()
        self.ready = True

    def add_file_to_index(self, file_id, file_path):
        return self.index_builder.build_file_index(
            file_id=file_id,
            file_path=file_path
        )

    def add_path_to_index(self, path):
        return self.index_builder.build_path_index(path)

    def delete_file_from_index(self, file_name):
        return self.index_builder.delete_file_by_name(file_name)

    def warmup_embedding(self):
        if self.embedder is None:
            return
        print("[Embedding] 正在 warmup...")
        _ = self.embedder.encode(["warmup text"])
        if torch.cuda.is_available():
            torch.cuda.synchronize()  # 确保 GPU 计算全部完成
        print("[Embedding] warmup 完成")

    def warmup_llm(self):
        if self.llm is None:
            return
        print("[LLM] 正在 warmup...")
        for _ in stream_chat_with_timing(self.llm,
                messages=[
                    {"role": "system", "content": "你是一个助手，请简短回答。"},
                    {"role": "user", "content": "你好"}
                ],
                context="",
                temperature=0.3,
                max_tokens=100,
                enable_thinking=False,
                rag_enabled=False
        ):
            pass
        if torch.cuda.is_available():
            torch.cuda.synchronize()
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

    def normalize_messages(self, messages, max_turns=6):
        normalized = []
        system_message = None
        for msg in messages or []:
            role = msg.get("role")
            content = (msg.get("content") or "").strip()
            if role not in {"system", "user", "assistant"} or not content:
                continue
            if role == "system":
                if system_message is None:
                    system_message = {"role": "system", "content": content}
                continue
            normalized.append({"role": role, "content": content})
        if max_turns > 0:
            normalized = normalized[-max_turns * 2:]
        return ([system_message] if system_message else []) + normalized

    def build_retrieval_query(self, messages, max_user_messages=3):
        user_messages = [
            msg.get("content", "").strip()
            for msg in messages
            if msg.get("role") == "user" and (msg.get("content") or "").strip()
        ]
        return "\n".join(user_messages[-max_user_messages:])

    def get_citation_details(self, chunk_uids):
        return resolve_citation(chunk_uids)

    def send(self, messages, file_ids=None, rag_top_k=10, tem=0.3, max_tokens=2048, thinking=True, rag_enabled=True, stop_event=None):
        file_ids = file_ids or []
        # query = self.get_last_user_message(messages)  # 废弃的无上下文对话
        # system_prompt = self.get_system_message(messages)
        normalized_messages = self.normalize_messages(messages)
        retrieval_query = self.build_retrieval_query(normalized_messages)
        if not self.ready:
            raise RuntimeError("RAG 服务尚未初始化")
        if self.llm is None:
            raise RuntimeError("LLM 尚未初始化，无法执行问答")
        if not retrieval_query:
            raise ValueError("缺少有效的用户问题，无法执行问答")
        context = ""
        if rag_enabled:
            results = retrieve_by_file_ids(
                query=retrieval_query,
                embedder=self.embedder,
                file_ids=file_ids,
                top_k=rag_top_k
            )
            context = build_context(results)
            # 流式输出
            for new_text in stream_chat_with_timing(
                    llm=self.llm,
                    messages=normalized_messages,
                    context=context,
                    temperature=tem,
                    max_tokens=max_tokens,
                    enable_thinking=thinking,
                    stop_event=stop_event,
                    rag_enabled=rag_enabled
            ):
                if stop_event is not None and stop_event.is_set():
                    break
                yield new_text

        else:
            context = ""
            for new_text in stream_chat_with_timing(
                    llm=self.llm,
                    messages=normalized_messages,
                    context=context,
                    temperature=tem,
                    max_tokens=max_tokens,
                    enable_thinking=thinking,
                    stop_event=stop_event,
                    rag_enabled=False
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
