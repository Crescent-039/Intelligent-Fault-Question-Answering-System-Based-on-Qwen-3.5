import torch
from threading import Thread
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer

from config import (
    LLM_MODEL_PATH,
    MAX_NEW_TOKENS,
    TEMPERATURE,
    TOP_P
)


class LLMModel:
    def __init__(self, model_path=LLM_MODEL_PATH, device=None):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

        print(f"[LLM] 使用设备: {self.device}")
        print(f"[LLM] 正在加载模型: {model_path}")

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            low_cpu_mem_usage=True,
            trust_remote_code=True
        ).to(self.device)

        self.model.eval()
        self.eos_token_ids = self._build_eos_token_ids()
        print("[LLM] 模型加载完成")

    def _build_eos_token_ids(self):
        """
        构造停止 token 列表。
        主要用于防止模型回答完后继续生成 user/assistant 等内容。
        """
        eos_token_ids = []
        # tokenizer 默认 eos
        if self.tokenizer.eos_token_id is not None:
            eos_token_ids.append(self.tokenizer.eos_token_id)
        # Qwen 常见结束符
        special_tokens = [
            "<|im_end|>",
            "<|endoftext|>"
        ]
        for token in special_tokens:
            token_id = self.tokenizer.convert_tokens_to_ids(token)
            if isinstance(token_id, int) and token_id >= 0:
                eos_token_ids.append(token_id)
        # 去重
        eos_token_ids = list(set(eos_token_ids))
        return eos_token_ids

    def chat(self, query, context):
        messages = [
            {
                "role": "system",
                "content": "你是一个文档问答助手。你必须严格依据提供的资料回答问题，不要凭空补充。如果资料中没有答案，请明确说“资料中没有提供相关信息”。"
            },
            {
                "role": "user",
                "content": f"资料如下：\n{context}\n\n问题：{query}"
            }
        ]

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False
        )

        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)

        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=True,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                use_cache=True,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )

        generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
        response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        return response

    def stream_chat(self, query, context, system_prompt=None, temperature=0.3, max_tokens=512, enable_thinking=False):
        """
        流式输出：返回一个生成器。
        使用方式：
            for text in llm.stream_chat(query, context):
                print(text, end="", flush=True)
        """
        default_system_prompt = (
            "你是一个文档问答助手。"
            "请严格依据资料回答问题。"
            "如果资料中没有答案，请说“资料中没有提供相关信息”。"
        )
        if system_prompt:
            final_system_prompt = (
                    default_system_prompt
                    + "\n\n用户自定义系统提示词：\n"
                    + system_prompt
            )
        else:
            final_system_prompt = default_system_prompt
        messages = [
            {
                "role": "system",
                "content": final_system_prompt
            },
            {
                "role": "user",
                "content": f"资料如下：\n{context}\n\n问题：{query}"
            }
        ]

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=enable_thinking
        )

        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)

        streamer = TextIteratorStreamer(
            tokenizer=self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True
        )
        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=0.9,
            use_cache=True,
            pad_token_id=self.tokenizer.eos_token_id,
            eos_token_id=self.tokenizer.eos_token_id
        )
        thread = Thread(
            target=self.model.generate,
            kwargs=generation_kwargs
        )
        thread.start()
        for new_text in streamer:
            yield new_text
        thread.join()

# --coding:utf-8--
