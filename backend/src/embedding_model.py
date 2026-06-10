import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel

from config import EMBED_MODEL_PATH, EMBED_BATCH_SIZE, EMBED_MAX_LENGTH


class EmbeddingModel:
    def __init__(self, model_path=EMBED_MODEL_PATH, device=None):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

        print(f"[Embedding] 使用设备: {self.device}")
        print(f"[Embedding] 正在加载模型: {model_path}")

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True
        )

        self.model = AutoModel.from_pretrained(
            model_path,
            trust_remote_code=True
        ).to(self.device)

        self.model.eval()
        print("[Embedding] 模型加载完成")

    def to_device(self, device):
        self.device = torch.device(device)
        self.model.to(self.device)
        self.model.eval()
        return self

    @staticmethod
    def mean_pooling(last_hidden_state, attention_mask):
        mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        masked_embeddings = last_hidden_state * mask
        summed = torch.sum(masked_embeddings, dim=1)
        counts = torch.clamp(mask.sum(dim=1), min=1e-9)
        return summed / counts

    def encode(self, texts, batch_size=EMBED_BATCH_SIZE, max_length=EMBED_MAX_LENGTH):
        if isinstance(texts, str):
            texts = [texts]

        all_embeddings = []

        with torch.inference_mode():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]

                inputs = self.tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=max_length,
                    return_tensors="pt"
                ).to(self.device)

                outputs = self.model(**inputs)

                embeddings = self.mean_pooling(
                    outputs.last_hidden_state,
                    inputs["attention_mask"]
                )

                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
                all_embeddings.append(embeddings.cpu().numpy())

        return np.vstack(all_embeddings).astype("float32")
# --coding:utf-8--
