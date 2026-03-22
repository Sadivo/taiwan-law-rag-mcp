"""
providers/local_providers.py
LocalEmbeddingProvider 與 LocalRerankingProvider
以 Wrapper 模式封裝現有 Embedder 與 Reranker 類別
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

import numpy as np

from .base import EmbeddingProvider, RerankingProvider
from .config import ProviderInitializationError

logger = logging.getLogger(__name__)


class LocalEmbeddingProvider(EmbeddingProvider):
    """封裝本地 Embedder，實作 EmbeddingProvider 介面"""

    def __init__(self, model_name: str = "Qwen/Qwen3-Embedding-4B", batch_size: Optional[int] = None):
        from indexing.embedder import Embedder  # lazy import to allow mocking
        try:
            self._embedder = Embedder(model_name=model_name, batch_size=batch_size)
        except Exception as exc:
            logger.error(
                "LocalEmbeddingProvider 初始化失敗：model_name=%s, error=%s",
                model_name,
                exc,
            )
            raise ProviderInitializationError(
                f"無法載入本地 Embedding 模型 '{model_name}': {exc}"
            ) from exc

        logger.info(
            "LocalEmbeddingProvider 初始化成功：provider_type=local, model_name=%s",
            self._embedder.model_name,
        )

    def embed_query(self, text: str) -> np.ndarray:
        return self._embedder.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[np.ndarray]:
        embeddings = self._embedder.model.encode(
            texts,
            batch_size=self._embedder.batch_size,
            normalize_embeddings=True,
            device=self._embedder.device,
            show_progress_bar=len(texts) > 100,
            convert_to_numpy=True,
        )
        return list(embeddings)

    @property
    def embedding_dim(self) -> int:
        return self._embedder.embedding_dim


class LocalRerankingProvider(RerankingProvider):
    """封裝本地 Reranker，實作 RerankingProvider 介面"""

    def __init__(self, model_name: str = "Qwen/Qwen3-Reranker-4B", device: Optional[str] = None):
        from retrieval.reranker import Reranker  # lazy import to allow mocking
        try:
            kwargs: Dict[str, Any] = {"model_name": model_name}
            if device is not None:
                kwargs["device"] = device
            self._reranker = Reranker(**kwargs)
        except Exception as exc:
            logger.error(
                "LocalRerankingProvider 初始化失敗：model_name=%s, error=%s",
                model_name,
                exc,
            )
            raise ProviderInitializationError(
                f"無法載入本地 Reranking 模型 '{model_name}': {exc}"
            ) from exc

        logger.info(
            "LocalRerankingProvider 初始化成功：provider_type=local, model_name=%s",
            self._reranker.model_name,
        )

    def rerank(self, query: str, docs: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        return self._reranker.rerank(query=query, docs=docs, top_k=top_k)
