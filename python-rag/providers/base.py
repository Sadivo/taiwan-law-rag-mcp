"""
providers/base.py
EmbeddingProvider 與 RerankingProvider 抽象介面
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

import numpy as np


class EmbeddingProvider(ABC):
    """向量化 Provider 抽象介面"""

    @abstractmethod
    def embed_query(self, text: str) -> np.ndarray:
        """將單一查詢文字轉換為向量"""
        ...

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[np.ndarray]:
        """將多筆文字批次轉換為向量列表"""
        ...

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """回傳向量維度，供維度驗證使用"""
        ...


class RerankingProvider(ABC):
    """重排序 Provider 抽象介面"""

    @abstractmethod
    def rerank(
        self,
        query: str,
        docs: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """對候選文件進行重排序，回傳前 top_k 筆"""
        ...
