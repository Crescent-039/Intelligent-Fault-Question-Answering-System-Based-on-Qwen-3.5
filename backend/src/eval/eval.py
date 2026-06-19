import argparse
import json
import re
import sys
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = Path(__file__).resolve().parent / "tmp"
sys.path.insert(0, str(SRC_ROOT))

import chat_with_doc_test as engine


REF_PATTERN = re.compile(r"\[r(\d+)\]")
PRINT_RAW_OUTPUT = False
PRINT_LLM_INPUT = False
OUTPUT_JSON_PATH = Path(__file__).resolve().parent / "eval_results.json"


def load_samples():
    samples = []
    for part in range(1, 6):
        query_path = TMP_DIR / f"query_part_{part}.json"
        answer_path = TMP_DIR / f"answer_part_{part}.json"
        queries = json.loads(query_path.read_text(encoding="utf-8"))
        answers = json.loads(answer_path.read_text(encoding="utf-8"))
        for query_item, answer_item in zip(queries, answers):
            samples.append({
                "part": part,
                "id": int(answer_item["id"]),
                "query": query_item["query"],
                "answer": answer_item["text"],
            })
    return samples


def unique_refs_in_order(text):
    seen = set()
    refs = []
    for match in REF_PATTERN.finditer(text):
        ref_id = int(match.group(1))
        if ref_id not in seen:
            seen.add(ref_id)
            refs.append(ref_id)
    return refs


def format_refs(refs):
    if not refs:
        return "无"
    return ", ".join(f"[r{ref_id}]" for ref_id in refs)


def evaluate_refs(gold_id, predicted_refs):
    accepted_refs = {gold_id - 1, gold_id, gold_id + 1}
    hit_refs = [ref_id for ref_id in predicted_refs if ref_id in accepted_refs]
    wrong_refs = [ref_id for ref_id in predicted_refs if ref_id not in accepted_refs]

    accuracy = 1.0 if hit_refs else 0.0

    return {
        "accepted_refs": sorted(accepted_refs),
        "hit_refs": hit_refs,
        "wrong_refs": wrong_refs,
        "accuracy": accuracy,
    }


def stream_answer(query, context, llm):
    pieces = []
    for new_text in llm.stream_chat(query, context):
        pieces.append(new_text)
    return "".join(pieces)


def get_judgement_label(item_metrics):
    return "对" if item_metrics["accuracy"] else "错"


def parse_args():
    parser = argparse.ArgumentParser(description="embedding 文档语义搜索评测")
    parser.add_argument("--top-k", type=int, default=engine.TOP_K, help="检索 top-k")
    parser.add_argument("--limit", type=int, default=0, help="只评测前 N 条，0 表示全部")
    parser.add_argument("--offset", type=int, default=0, help="跳过前 N 条后开始评测")
    return parser.parse_args()


def main():
    args = parse_args()

    print("===== 加载评测数据 =====")
    samples = load_samples()
    if args.offset:
        samples = samples[args.offset:]
    if args.limit:
        samples = samples[:args.limit]
    total = len(samples)
    print(f"样本数: {total}")

    print("\n===== 加载检索与生成内核 =====")
    chunk_records = engine.load_json(engine.CHUNKS_PATH)
    index = engine.faiss.read_index(engine.FAISS_INDEX_PATH)
    embedder = engine.EmbeddingModel(device="cuda")
    llm = engine.LLMModel()

    stats = {
        "accuracy": 0.0,
    }
    records = []

    print("\n===== 开始评测 =====")
    print("输出字段: 题号 | 判定 | refs | chunk_id | 累计 Accuracy")

    for idx, sample in enumerate(samples, start=1):
        gold_id = sample["id"]
        query = sample["query"]

        results = engine.retrieve(query, embedder, index, chunk_records, top_k=args.top_k)
        chunk_ids = [item["chunk_id"] for item in results]

        context = engine.build_context(results)
        if PRINT_LLM_INPUT:
            print(f"llm_query={query}")
            print(f"llm_context={context}")
            print(f"llm_input_view=问题:\n{query}\n\n上下文:\n{context}")
        answer = stream_answer(query, context, llm)
        predicted_refs = unique_refs_in_order(answer)
        item_metrics = evaluate_refs(gold_id, predicted_refs)
        judgement = get_judgement_label(item_metrics)

        stats["accuracy"] += item_metrics["accuracy"]

        print(
            f"第{idx}题 | {judgement} | "
            f"refs={format_refs(predicted_refs)} | "
            f"chunk_id={chunk_ids if chunk_ids else '[]'} | "
            f"Accuracy={stats['accuracy'] / idx:.4f}"
        )
        if PRINT_RAW_OUTPUT:
            print(f"raw_output={answer}")

        records.append({
            "index": idx,
            "part": sample["part"],
            "id": gold_id,
            "query": query,
            "gold_answer": sample["answer"],
            "llm_input": {
                "query": query,
                "context": context,
                "input_view": f"问题:\n{query}\n\n上下文:\n{context}",
            },
            "llm_output": {
                "raw_output": answer,
                "extracted_refs": predicted_refs,
            },
            "retrieval": {
                "top_k": args.top_k,
                "chunk_ids": chunk_ids,
                "results": results,
            },
            "evaluation": {
                "judgement": judgement,
                "accepted_refs": item_metrics["accepted_refs"],
                "hit_refs": item_metrics["hit_refs"],
                "wrong_refs": item_metrics["wrong_refs"],
                "accuracy": item_metrics["accuracy"],
            },
            "running_metrics": {
                "accuracy": stats["accuracy"] / idx,
            },
        })

    summary = {
        "sample_count": total,
        "accuracy": stats["accuracy"] / total,
    }
    output_payload = {
        "config": {
            "top_k": args.top_k,
            "offset": args.offset,
            "limit": args.limit,
            "print_raw_output": PRINT_RAW_OUTPUT,
            "print_llm_input": PRINT_LLM_INPUT,
        },
        "summary": summary,
        "records": records,
    }
    OUTPUT_JSON_PATH.write_text(
        json.dumps(output_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n{'=' * 100}")
    print("===== 最终结果 =====")
    print(f"样本总数: {total}")
    print(f"Accuracy : {summary['accuracy']:.4f}")
    print(f"JSON结果  : {OUTPUT_JSON_PATH}")


if __name__ == "__main__":
    main()
