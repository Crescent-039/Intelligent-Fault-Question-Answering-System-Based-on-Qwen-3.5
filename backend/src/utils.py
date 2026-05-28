import json
import os
import re


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def load_text(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text):
    """按中英文标点分句（简单但实用）"""
    # 匹配句号、问号、感叹号、换行等作为句子结束标志
    sentences = re.split(r'(?<=[。！？.!?\n])\s*', text)
    # 过滤掉空句子
    return [s.strip() for s in sentences if s.strip()]


def chunk_text_by_sentences(text, chunk_size=200, overlap_sentences=2):
    """
    按句子边界切块，每个块尽量接近 chunk_size 个字符，
    且块与块之间重叠指定数量的句子。
    """
    sentences = split_sentences(text)
    chunks = []
    i = 0
    while i < len(sentences):
        current_chunk = []
        current_len = 0
        # 从第 i 句开始累积，直到超过 chunk_size 或句子用完
        j = i
        while j < len(sentences):
            sent = sentences[j]
            # 预测加入后会不会太长（第一个句子直接加）
            if current_len + len(sent) > chunk_size and current_chunk:
                break  # 已经够了，这个句子留给下一块
            current_chunk.append(sent)
            current_len += len(sent)
            j += 1

        chunk_text = " ".join(current_chunk)
        chunks.append(chunk_text)

        # 下一块的起始句子：从 i 开始，向前移动 (当前块句子数 - overlap_sentences)
        num_sents_in_chunk = len(current_chunk)
        step = max(1, num_sents_in_chunk - overlap_sentences)
        i += step

        # 如果已经到末尾，退出
        if i >= len(sentences):
            break

    return chunks


def save_json(data, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
# --coding:utf-8--
