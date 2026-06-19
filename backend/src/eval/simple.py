import json
import random
from pathlib import Path


base_dir = Path(__file__).resolve().parents[2]
input_path = base_dir / "data" / "chunks.json"
output_dir = base_dir / "src" / "eval" / "tmp"

with input_path.open("r", encoding="utf-8") as f:
    chunks = json.load(f)

sampled = random.sample(chunks, 200)
result = [{"id": item["id"], "text": item["text"]} for item in sampled]
frame = [{"id": item["id"], "query": ""} for item in sampled]

for i in range(5):
    part = result[i * 40:(i + 1) * 40]
    output_path = output_dir / f"answer_part_{i + 1}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(part, f, ensure_ascii=False, indent=2)

for j in range(5):
    part = frame[j * 40:(j + 1) * 40]
    output_path = output_dir / f"query_part_{j + 1}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(part, f, ensure_ascii=False, indent=2)
