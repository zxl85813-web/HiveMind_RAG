"""
基于语言与语义的切分器体系 (Splitting & Chunking)
替代 `langchain` 的粗暴按字数切片，适用于入库和记忆总结前的长文本智能切断。

5.3 核心算法库重构：
  SemanticSplitter  — 滑动余弦相似度窗口，在主题转换处切分（实语义切分）。
  TokenSplitter     — 基于 tiktoken 精准 Token 上限切分，替代字符估算。
"""

import math
import re
from abc import ABC, abstractmethod

from loguru import logger


def _cosine(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    return dot / (n1 * n2) if n1 and n2 else 0.0


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation boundaries (CN + EN)."""
    raw = re.split(r"(?<=[。？！\.\?!])\s*", text)
    # Re-join very short fragments (< 8 chars) with the previous sentence
    sentences: list[str] = []
    for s in raw:
        s = s.strip()
        if not s:
            continue
        if sentences and len(s) < 8:
            sentences[-1] = sentences[-1] + s
        else:
            sentences.append(s)
    return sentences or [text]


class BaseSplitter(ABC):
    """文本切分器接口"""

    @abstractmethod
    def split_text(self, text: str) -> list[str]:
        """将长文本分解为多段。"""
        pass


class SemanticSplitter(BaseSplitter):
    """
    5.3 实语义切分器：
    - 将文本切成句子 → 计算相邻句对的 Cosine 相似度 → 相似度骤降处切块。
    - 滑动窗口平均：`window` 个句子的平均相似度，更平滑，减少单句噪音。
    - 硬上限：累积句子达到 `max_chunk_size` 字符时强制切块（防止超长）。

    如果 Embedding 服务不可用，自动降级为按空行切分（原有行为）。
    """

    def __init__(
        self,
        max_chunk_size: int = 512,
        overlap: int = 50,
        similarity_threshold: float = 0.75,
        window: int = 3,
    ):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.similarity_threshold = similarity_threshold
        self.window = window

    def split_text(self, text: str) -> list[str]:
        if not text.strip():
            return []

        sentences = _split_sentences(text)
        if len(sentences) <= 1:
            return [text]

        try:
            return self._semantic_split(sentences)
        except Exception as e:
            logger.warning(f"[SemanticSplitter] Embedding unavailable ({e}), falling back to paragraph split.")
            return [c for c in text.split("\n\n") if c.strip()] or [text]

    def _semantic_split(self, sentences: list[str]) -> list[str]:
        from app.core.embeddings import get_embedding_service

        emb_service = get_embedding_service()
        embeddings = [emb_service.embed_query(s) for s in sentences]

        chunks: list[str] = []
        current: list[str] = [sentences[0]]
        current_len: int = len(sentences[0])

        for i in range(1, len(sentences)):
            # Sliding average similarity over the `window` previous sentences
            window_start = max(0, i - self.window)
            sim_scores = [_cosine(embeddings[j], embeddings[i]) for j in range(window_start, i)]
            avg_sim = sum(sim_scores) / len(sim_scores) if sim_scores else 1.0

            # Force break if hard size limit reached
            force_break = current_len + len(sentences[i]) > self.max_chunk_size

            if avg_sim < self.similarity_threshold or force_break:
                chunks.append(" ".join(current))
                # Overlap: carry last `overlap` chars worth of sentences
                carried: list[str] = []
                carried_len = 0
                for s in reversed(current):
                    if carried_len + len(s) > self.overlap:
                        break
                    carried.insert(0, s)
                    carried_len += len(s)
                current = carried + [sentences[i]]
                current_len = sum(len(s) for s in current)
            else:
                current.append(sentences[i])
                current_len += len(sentences[i])

        if current:
            chunks.append(" ".join(current))

        logger.debug(f"[SemanticSplitter] {len(sentences)} sentences → {len(chunks)} chunks")
        return chunks


class TokenSplitter(BaseSplitter):
    """
    5.3 精准 Token 切分器：
    - 使用 tiktoken 准确计量 Token 数，而非字符估算。
    - 按句子边界切分（不在词中间截断）。
    - 支持 `overlap` Token 数的滑动窗口以保留前后文。
    """

    def __init__(self, max_tokens: int = 1000, overlap_tokens: int = 50, model: str = "gpt-4o"):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.model = model

    def split_text(self, text: str) -> list[str]:
        if not text.strip():
            return []

        from app.core.algorithms.token_service import token_service

        # Fast path: text fits in one chunk
        if token_service.count_tokens(text, self.model) <= self.max_tokens:
            return [text]

        sentences = _split_sentences(text)
        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0

        for sent in sentences:
            sent_tokens = token_service.count_tokens(sent, self.model)

            # If a single sentence is larger than the budget, hard-truncate it
            if sent_tokens > self.max_tokens:
                if current:
                    chunks.append(" ".join(current))
                    current = []
                    current_tokens = 0
                chunks.append(token_service.truncate_to_budget(sent, self.max_tokens, self.model))
                continue

            if current_tokens + sent_tokens > self.max_tokens:
                chunks.append(" ".join(current))
                # Re-seed with overlap sentences from the end of current
                overlap_buf: list[str] = []
                overlap_tok = 0
                for s in reversed(current):
                    t = token_service.count_tokens(s, self.model)
                    if overlap_tok + t > self.overlap_tokens:
                        break
                    overlap_buf.insert(0, s)
                    overlap_tok += t
                current = overlap_buf
                current_tokens = overlap_tok

            current.append(sent)
            current_tokens += sent_tokens

        if current:
            chunks.append(" ".join(current))

        logger.debug(f"[TokenSplitter] Split into {len(chunks)} chunks (max_tokens={self.max_tokens})")
        return chunks


semantic_splitter = SemanticSplitter()

