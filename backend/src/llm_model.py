import torch
from threading import Thread, Event
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer, \
    StoppingCriteria, StoppingCriteriaList
from transformers.generation import LogitsProcessor, LogitsProcessorList


from config import (
    LLM_MODEL_PATH,
    MAX_NEW_TOKENS,
    TEMPERATURE,
    TOP_P
)


# 接收到前端停止信号后的停止事件
class StopOnEvent(StoppingCriteria):
    def __init__(self, stop_event: Event):
        self.stop_event = stop_event

    def __call__(self, input_ids, scores, **kwargs):
        return self.stop_event.is_set()


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

    def stream_chat(
            self,
            messages,
            context,
            temperature=0.3,
            max_tokens=512,
            enable_thinking=False,
            stop_event=None,
            rag_enabled=True
    ):
        """
        流式输出：返回一个生成器。
        使用方式：
            for text in llm.stream_chat(query, context):
                print(text, end="", flush=True)
        """
        self_intro_prompt = (
            """
            当用户询问你的身份、能力、功能、使用方式，或表达类似“你是谁”“你能做什么”“介绍一下你自己”“怎么使用你”“你可以帮我什么”等意图时，你应主动介绍自己的功能。
            介绍内容应包括：
            1、你是一个 AI 助手。
            2、你可以进行问答、总结、改写、翻译、解释概念、生成内容、辅助分析和提供建议。
            3、如果当前启用了文档问答能力，你还可以基于用户提供或系统检索到的资料回答问题，并在需要时给出引用。
            4、如果当前未启用文档问答能力，你会基于通用知识和用户提供的信息进行回答。
            5、不要声称自己具备系统实际没有提供的能力，例如访问实时互联网、读取用户本地文件、执行外部操作等。
            6、除非用户要求，否则在自我介绍时不要引用资料、不要输出参考文档、不要使用类似 [r1043] 的引用标记。
            """
        )

        thinking_prompt = (
            """
            在开启思考模式的情况下，你应当在思考模式前固定输出"Thinking Process:"这几个字符
            """
        )

        system_prompt = ""
        conversation_messages = []
        for message in messages or []:
            role = message.get("role")
            content = (message.get("content") or "").strip()
            if role == "system" and not system_prompt:
                system_prompt = content
                continue
            if role in {"user", "assistant"} and content:
                conversation_messages.append({"role": role, "content": content})

        if not conversation_messages or conversation_messages[-1]["role"] != "user":
            raise ValueError("消息列表必须以用户消息结尾")

        if rag_enabled:
            default_system_prompt = (
                f"""
                你是一个文档问答助手。
                请严格依据资料回答问题。
                每份参考资料都有一个唯一的锚点标记（Anchor），格式为 [r数字]，例如 [r1043]。
                你必须严格遵守以下规则：
                1、**仅基于参考资料回答**
                  只能使用上述资料中的信息，不得使用外部知识或凭空编造。
                  若资料中没有足够信息，直接回复：“根据现有资料无法回答”。
                2、**引用方式**"
                   当你依据或引用某个资料的内容时，必须在对应的句子末尾加上该资料的锚点标记，例如 [r1043]。
                   如果一个观点同时来源于多个资料，可以合并标记，如 [r1043][r207]。
                   回答中如需引用资料来源，请使用 Anchor 格式，例如 [r1043]，切记不要加引号。
                3、**回答末尾的参考文档**
                   在完整回答的最后，必须另起一行，列出本次回答中实际引用到的所有锚点，格式为：参考文档：[r1043], [r207]
                   如果未引用任何资料（即回答“无法回答”时），则写：参考文档：无。
                4、**回答风格**
                    语言准确、简洁，重点突出。
                   不要说明你正在“根据资料回答”，直接给出答案和引用。
                如果资料中没有答案，请说“资料中没有提供相关信息”。
                5、**条件限制**
                类似[r1043]的anchor标记请在每一句回答的句号后输出。
                {self_intro_prompt}
                特殊规则：
                当用户是在询问你的身份、能力或使用方式时，可以直接介绍你的功能，不需要强行依据资料回答，也不需要引用资料，也不要使用类似 [r1043] 的引用标记。
                """
            )
        else:
            default_system_prompt = (
                f"""
                你是一个专业、可靠的 AI 助手。
                请根据用户的问题直接作答，要求：
                1、回答应准确、清晰、简洁。
                2、如果问题需要推理，请给出必要的推理过程，但避免冗长。
                3、如果用户的问题信息不足，请主动说明缺少哪些信息，并给出合理的下一步建议。
                4、如果你不确定答案，请明确说明不确定，不要编造。
                5、除非用户要求，否则不要引用资料、不要输出参考文档、不要使用类似 [r1043] 的引用标记。
                6、保持自然、友好、专业的表达风格。
                {self_intro_prompt}
                """
            )
        final_system_prompt = default_system_prompt
        if system_prompt:
            final_system_prompt += "\n\n用户自定义系统提示词：\n" + system_prompt

        if enable_thinking:
            thinking_system_prompt = thinking_prompt
        else:
            thinking_system_prompt = ""

        final_messages = [
            {"role": "system", "content": final_system_prompt + thinking_system_prompt},
            *conversation_messages
        ]

        if rag_enabled and context:
            last_user_content = final_messages[-1]["content"]
            final_messages[-1] = {
                "role": "user",
                "content": f"参考资料如下：\n{context}\n\n请结合以上资料和对话历史回答用户当前问题。\n当前问题：{last_user_content}"
            }

        text = self.tokenizer.apply_chat_template(
            final_messages,
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

        # 构建 logits_processor
        logits_processor = LogitsProcessorList()
        if enable_thinking:
            # 实例化自定义的拦截器，限制思考 token 不超过 300
            logits_processor.append(
                ThinkingTokenBudgetProcessor(self.tokenizer, max_thinking_tokens=1700)
            )

        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=max_tokens,
            logits_processor=logits_processor,
            do_sample=True,
            temperature=temperature,
            top_p=0.9,
            use_cache=True,
            pad_token_id=self.tokenizer.eos_token_id,
            eos_token_id=self.tokenizer.eos_token_id
        )
        if stop_event is not None:
            generation_kwargs["stopping_criteria"] = StoppingCriteriaList([StopOnEvent(stop_event)])

        thread = Thread(
            target=self.model.generate,
            kwargs=generation_kwargs
        )
        thread.start()
        for new_text in streamer:
            yield new_text
        thread.join()


class ThinkingTokenBudgetProcessor(LogitsProcessor):
    """
    通过自定义 LogitsProcessor 限制模型的思考长度。
    当生成的 token 数量接近限制时，柔性引导模型收敛并输出 </think>；
    当达到限制时，硬性强制输出 </think> 标签，从而完美规避参数校验报错。
    """

    def __init__(self, tokenizer, max_thinking_tokens=1000):
        self.tokenizer = tokenizer
        self.max_thinking_tokens = max_thinking_tokens

        # 提取结束符和换行符在当前 tokenizer 中的 ID
        self.think_end_token = self.tokenizer.encode("</think>", add_special_tokens=False)[0]
        self.nl_token = self.tokenizer.encode("\n", add_special_tokens=False)[0]

        self.tokens_generated = 0
        self.stopped_thinking = False
        self.neg_inf = float('-inf')

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        self.tokens_generated += 1

        if self.max_thinking_tokens is not None and not self.stopped_thinking:
            # 1. 柔性过渡阶段（消耗达到 95% 以上）：微调换行符和结束符概率，促使模型平滑收尾
            if (self.tokens_generated / self.max_thinking_tokens) > 0.95:
                for i in range(scores.shape[0]):
                    scores[i][self.nl_token] = scores[i][self.think_end_token] * (
                                1 + (self.tokens_generated / self.max_thinking_tokens))
                    scores[i][self.think_end_token] = scores[i][self.think_end_token] * (
                                1 + (self.tokens_generated / self.max_thinking_tokens))

            # 2. 硬性截断阶段：倒数第二步强制换行，最后一步强制输出 </think>
            if self.tokens_generated >= (self.max_thinking_tokens - 1):
                for i in range(scores.shape[0]):
                    new_scores = torch.full_like(scores[i], self.neg_inf)
                    if self.tokens_generated == self.max_thinking_tokens - 1:
                        new_scores[self.nl_token] = 0.0
                    else:
                        new_scores[self.think_end_token] = 0.0
                        self.stopped_thinking = True
                    scores[i] = new_scores
                return scores

        return scores
# --coding:utf-8--
