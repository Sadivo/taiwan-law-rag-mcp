"""
tests/test_retrieval_service.py
Unit tests for RetrievalService
"""
from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from providers.config import DimensionMismatchError
from retrieval.retrieval_service import RetrievalService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_embedding_provider(dim: int) -> MagicMock:
    provider = MagicMock()
    provider.embed_query.return_value = np.zeros(dim, dtype="float32")
    provider.embedding_dim = dim
    return provider


def _make_reranking_provider(return_docs: List[Dict[str, Any]] | None = None) -> MagicMock:
    provider = MagicMock()
    provider.rerank.return_value = return_docs or []
    return provider


def _make_hybrid_retriever(index_dim: int | None = None, chunks: list | None = None) -> MagicMock:
    retriever = MagicMock()
    # vector_retriever
    vr = MagicMock()
    vr.chunks = chunks or []
    if index_dim is not None:
        index = MagicMock()
        index.d = index_dim
        vr.index = index
    else:
        vr.index = None
    retriever.vector_retriever = vr
    retriever.search.return_value = []
    return retriever


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDimensionCheck:
    def test_dimension_mismatch_raises(self):
        """embedding dim=512 vs FAISS index dim=1024 → DimensionMismatchError"""
        emb = _make_embedding_provider(dim=512)
        rnk = _make_reranking_provider()
        hr = _make_hybrid_retriever(index_dim=1024)

        with pytest.raises(DimensionMismatchError) as exc_info:
            RetrievalService(emb, rnk, hr)

        msg = str(exc_info.value)
        assert "512" in msg
        assert "1024" in msg

    def test_dimension_match_succeeds(self):
        """matching dims → no error"""
        emb = _make_embedding_provider(dim=1024)
        rnk = _make_reranking_provider()
        hr = _make_hybrid_retriever(index_dim=1024)

        # Should not raise
        service = RetrievalService(emb, rnk, hr)
        assert service is not None

    def test_no_index_skips_dimension_check(self):
        """index=None → skip dimension check, no error"""
        emb = _make_embedding_provider(dim=512)
        rnk = _make_reranking_provider()
        hr = _make_hybrid_retriever(index_dim=None)

        service = RetrievalService(emb, rnk, hr)
        assert service is not None


class TestSearchSemantic:
    def test_search_semantic_uses_providers(self):
        """search_semantic calls hybrid_retriever.search and reranking_provider.rerank"""
        dim = 256
        emb = _make_embedding_provider(dim=dim)
        docs = [{"id": "1", "law_name": "勞動基準法", "rrf_score": 0.9}]
        rnk = _make_reranking_provider(return_docs=docs)
        hr = _make_hybrid_retriever(index_dim=dim)
        hr.search.return_value = docs

        service = RetrievalService(emb, rnk, hr)
        results = service.search_semantic("加班費", top_k=5)

        hr.search.assert_called_once_with("加班費", top_k=10)  # top_k * 2
        rnk.rerank.assert_called_once()
        assert results == docs

    def test_search_semantic_filter_category(self):
        """filter_category filters candidates before reranking"""
        dim = 256
        emb = _make_embedding_provider(dim=dim)
        rnk = _make_reranking_provider(return_docs=[])
        hr = _make_hybrid_retriever(index_dim=dim)
        hr.search.return_value = [
            {"id": "1", "law_category": "行政", "rrf_score": 0.9},
            {"id": "2", "law_category": "民事", "rrf_score": 0.8},
        ]

        service = RetrievalService(emb, rnk, hr)
        service.search_semantic("test", top_k=5, filter_category="行政")

        # rerank should only receive the filtered doc
        call_args = rnk.rerank.call_args
        candidates_passed = call_args[0][1]
        assert len(candidates_passed) == 1
        assert candidates_passed[0]["law_category"] == "行政"


class TestSearchExact:
    def _make_service(self, chunks: list) -> RetrievalService:
        dim = 256
        emb = _make_embedding_provider(dim=dim)
        rnk = _make_reranking_provider()
        hr = _make_hybrid_retriever(index_dim=dim, chunks=chunks)
        return RetrievalService(emb, rnk, hr)

    def test_exact_query_returns_matching_chunk(self):
        chunks = [
            {"id": "c1", "law_name": "勞動基準法", "article_no": "第 38 條", "content": "特休假"},
            {"id": "c2", "law_name": "民法", "article_no": "第 184 條", "content": "侵權行為"},
        ]
        service = self._make_service(chunks)
        results = service.search_exact("勞動基準法第38條")
        assert len(results) == 1
        assert results[0]["article_no"] == "第 38 條"

    def test_semantic_query_returns_empty(self):
        chunks = [{"id": "c1", "law_name": "勞動基準法", "article_no": "第 38 條", "content": "特休假"}]
        service = self._make_service(chunks)
        results = service.search_exact("加班費如何計算")
        assert results == []


class TestSearchLaw:
    def _make_service(self, chunks: list) -> RetrievalService:
        dim = 256
        emb = _make_embedding_provider(dim=dim)
        rnk = _make_reranking_provider()
        hr = _make_hybrid_retriever(index_dim=dim, chunks=chunks)
        return RetrievalService(emb, rnk, hr)

    def test_search_law_filters_by_name(self):
        chunks = [
            {"id": "c1", "law_name": "勞動基準法", "article_no": "第 1 條", "is_abolished": False},
            {"id": "c2", "law_name": "民法", "article_no": "第 1 條", "is_abolished": False},
        ]
        service = self._make_service(chunks)
        results = service.search_law("勞動基準法")
        assert all(r["law_name"] == "勞動基準法" for r in results)
        assert len(results) == 1

    def test_search_law_excludes_abolished_by_default(self):
        chunks = [
            {"id": "c1", "law_name": "舊法", "article_no": "第 1 條", "is_abolished": True},
            {"id": "c2", "law_name": "舊法", "article_no": "第 2 條", "is_abolished": False},
        ]
        service = self._make_service(chunks)
        results = service.search_law("舊法", include_abolished=False)
        assert len(results) == 1
        assert results[0]["article_no"] == "第 2 條"

    def test_search_law_includes_abolished_when_requested(self):
        chunks = [
            {"id": "c1", "law_name": "舊法", "article_no": "第 1 條", "is_abolished": True},
            {"id": "c2", "law_name": "舊法", "article_no": "第 2 條", "is_abolished": False},
        ]
        service = self._make_service(chunks)
        results = service.search_law("舊法", include_abolished=True)
        assert len(results) == 2


class TestRebuildIndex:
    def test_rebuild_index_returns_not_implemented(self):
        dim = 256
        emb = _make_embedding_provider(dim=dim)
        rnk = _make_reranking_provider()
        hr = _make_hybrid_retriever(index_dim=dim)
        service = RetrievalService(emb, rnk, hr)

        result = service.rebuild_index(force=True)
        assert result["status"] == "not_implemented"
        assert "message" in result
