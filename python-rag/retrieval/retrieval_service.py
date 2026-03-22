"""
retrieval/retrieval_service.py
RetrievalService - 整合 EmbeddingProvider、RerankingProvider 與 HybridRetriever
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from providers.base import EmbeddingProvider, RerankingProvider
from providers.config import DimensionMismatchError
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.query_classifier import QueryClassifier

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    整合 Provider 與 HybridRetriever 的上層服務，供 FastAPI 路由使用。
    初始化時進行向量維度驗證（fail-fast）。
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        reranking_provider: RerankingProvider,
        hybrid_retriever: HybridRetriever,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.reranking_provider = reranking_provider
        self.hybrid_retriever = hybrid_retriever
        self._query_classifier = QueryClassifier()

        # 維度驗證
        test_vec = embedding_provider.embed_query("test")
        actual_dim = int(test_vec.shape[0])

        index = getattr(hybrid_retriever.vector_retriever, "index", None)
        if index is not None:
            index_dim = int(index.d)
            if actual_dim != index_dim:
                raise DimensionMismatchError(
                    f"Embedding dim {actual_dim} != FAISS index dim {index_dim}"
                )

        # 將 embedding_provider 注入 HybridRetriever，讓它使用 Provider 產生向量
        hybrid_retriever.embedder = embedding_provider
        logger.info(
            "RetrievalService initialized with embedding_provider=%s, reranking_provider=%s",
            type(embedding_provider).__name__,
            type(reranking_provider).__name__,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_semantic(
        self,
        query: str,
        top_k: int,
        filter_category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """語義搜尋：混合檢索 → 類別過濾 → Reranking"""
        candidates = self.hybrid_retriever.search(query, top_k=top_k * 2)

        if filter_category:
            candidates = [
                doc for doc in candidates
                if doc.get("law_category", "") == filter_category
            ]

        results = self.reranking_provider.rerank(query, candidates, top_k)
        return results

    def search_exact(self, query: str) -> List[Dict[str, Any]]:
        """精確搜尋：依條號與法律名稱查找 chunk"""
        from data_processing.law_aliases import normalize_law_name

        parsed = self._query_classifier.classify(query)
        chunks = self.hybrid_retriever.vector_retriever.chunks

        if parsed["type"] != "exact":
            return []

        law_name = parsed.get("law_name")
        article_no = parsed.get("article_no")

        # 將別名轉為正式名稱（例如「勞基法」→「勞動基準法」）
        if law_name:
            law_name = normalize_law_name(law_name)

        results = []
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            chunk_law = chunk.get("law_name") or meta.get("law_name", "")
            chunk_article = chunk.get("article_no") or meta.get("article_no", "")

            law_match = (law_name is None) or (chunk_law == law_name)
            article_match = (article_no is None) or (chunk_article == article_no)

            if law_match and article_match:
                flat = _flatten_chunk(chunk)
                results.append(flat)

        return results

    def search_law(
        self,
        law_name: str,
        include_abolished: bool = False,
    ) -> List[Dict[str, Any]]:
        """依法律名稱搜尋所有相關 chunk"""
        chunks = self.hybrid_retriever.vector_retriever.chunks
        results = []
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            chunk_law = chunk.get("law_name") or meta.get("law_name", "")
            if chunk_law != law_name:
                continue
            is_abolished = chunk.get("is_abolished") or meta.get("is_abolished", False)
            if not include_abolished and is_abolished:
                continue
            results.append(_flatten_chunk(chunk))
        return results

    def get_law_full(self, law_name: str) -> Dict[str, Any]:
        """取得某部法律的完整資訊（法律 metadata + 所有條文）"""
        articles_raw = self.search_law(law_name, include_abolished=True)

        law_meta: Dict[str, Any] = {}
        articles: List[Dict[str, Any]] = []

        for chunk in articles_raw:
            if not law_meta:
                law_meta = {
                    "law_name": chunk.get("law_name", law_name),
                    "law_level": chunk.get("law_level", ""),
                    "law_category": chunk.get("law_category", ""),
                    "law_url": chunk.get("law_url", ""),
                    "modified_date": chunk.get("modified_date", ""),
                    "is_abolished": chunk.get("is_abolished", False),
                }
            articles.append({
                "article_no": chunk.get("article_no", ""),
                "content": chunk.get("content", ""),
                "chapter": chunk.get("chapter", ""),
            })

        if not law_meta:
            law_meta = {
                "law_name": law_name,
                "law_level": "",
                "law_category": "",
                "law_url": "",
                "modified_date": "",
                "is_abolished": False,
            }

        return {"law": law_meta, "articles": articles}

    def compare_laws(
        self,
        law_names: List[str],
        topic: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """比較多部法律中與 topic 相關的條文"""
        result: Dict[str, List[Dict[str, Any]]] = {}
        for law_name in law_names:
            candidates = self.hybrid_retriever.search(topic, top_k=20)
            relevant = [
                _flatten_chunk(doc) for doc in candidates
                if (doc.get("law_name") or doc.get("metadata", {}).get("law_name", "")) == law_name
            ]
            result[law_name] = relevant
        return result

    def rebuild_index(self, force: bool = False) -> Dict[str, Any]:
        """索引重建（佔位實作，實際重建需透過 CLI）"""
        return {
            "status": "not_implemented",
            "message": "Index rebuild not supported via API",
        }


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _flatten_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """將 chunk 的 metadata 欄位提升至頂層，方便序列化"""
    flat = dict(chunk)
    meta = flat.pop("metadata", {}) or {}
    for k, v in meta.items():
        if k not in flat:
            flat[k] = v
    return flat
