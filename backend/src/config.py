import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 模型路径
LLM_MODEL_PATH = os.path.join(BASE_DIR, "Qwen3.5-4B")
EMBED_MODEL_PATH = os.path.join(BASE_DIR, "Qwen3-Embedding-4B")

# 文档路径
DOC_PATH = os.path.join(BASE_DIR, "docs", "demo.txt")

# 数据保存路径
DATA_DIR = os.path.join(BASE_DIR, "data")
FAISS_INDEX_PATH = os.path.join(DATA_DIR, "faiss.index")
CHUNKS_PATH = os.path.join(DATA_DIR, "chunks.json")

# 切块参数
CHUNK_SIZE = 200
CHUNK_OVERLAP = 50

# 检索参数
TOP_K = 10

# embedding 参数
EMBED_BATCH_SIZE = 8
EMBED_MAX_LENGTH = 512

# 生成参数
MAX_NEW_TOKENS = 3072
TEMPERATURE = 0.3
TOP_P = 0.9
# --coding:utf-8--
