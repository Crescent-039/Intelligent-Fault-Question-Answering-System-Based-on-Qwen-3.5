import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

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
        print("[LLM] 模型加载完成")

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
            add_generation_prompt=True
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
                pad_token_id=self.tokenizer.eos_token_id
            )

        generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
        response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        return response
# --coding:utf-8--
