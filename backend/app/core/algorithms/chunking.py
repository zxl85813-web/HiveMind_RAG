"""
基于语言与语义的切分器体系 (Splitting & Chunking)
替代 `langchain` 的粗暴按字数切片。这里将涵盖入库和记忆总结前的长文本智能切断。
"""

from abc import ABC, abstractmethod


class BaseSplitter(ABC):
    """文本切分器接口"""

    @abstractmethod
    def split_text(self, text: str) -> list[str]:
        """将长文本分解为多段。"""
        pass


class SemanticSplitter(BaseSplitter):
    """基于特定标点符号、段落缩进或相似度变化分块。"""

    def __init__(self, max_chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = max_chunk_size
        self.overlap = overlap

    def split_text(self, text: str) -> list[str]:
        # TODO: 接入真正 Semantic Chunking 逻辑
        # Currently a fallback implementation based on naive line split to start
        return text.split("\n\n")


class TokenSplitter(BaseSplitter):
    """纯粹的按 Token 上限无情切分，应对极端长文本的临时切分。"""

    def __init__(self, max_tokens: int = 1000):
        self.max_tokens = max_tokens

    def split_text(self, text: str) -> list[str]:
        # TODO: Need TokenService usage here
        return [text]


semantic_splitter = SemanticSplitter()
