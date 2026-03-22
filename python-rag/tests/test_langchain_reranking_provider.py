"""
tests/test_langchain_reranking_provider.py
Task 5 測試：LangChainRerankingProvider 屬性測試與單元測試
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from providers.config import ProviderConfig, ProviderConfigError
from providers.langchain_providers import LangChainRerankingProvider


# ---------------------------------------------------------------------------
# 輔助：建立帶有 mock compressor 的 provider
# ---------------------------------------------------------------------------

def _make_provider(
    api_key: str = "test-cohere-key",
    model_name: str | None = None,
    mock_compressor: MagicMock | None = None,
) -> LangChainRerankingProvider:
    """建立 LangChainRerankingProvider，並注入 mock _compressor"""
    config = ProviderConfig(
        provider_type="cohere",
        model_name=model_name,
        api_key=api_key,
    )
    with patch.object(LangChainRerankingProvider, "_init_cohere", return_value=mock_compressor or MagicMock()):
        provider = LangChainRerankingProvider(config)
    if mock_compressor is not None:
        provider._compressor = mock_compressor
    return provider


def _make_docs(n: int, rrf_scores: List[float] | None = None) -> List[Dict[str, Any]]:
    """建立測試用文件列表"""
    scores = rrf_scores if rrf_scores is not None else [float(i) for i in range(n)]
    return [
        {"id": f"doc_{i}", "content": f"content {i}", "rrf_score": scores[i]}
        for i in range(n)
    ]


# ===========================================================================
# Sub-task 5.1：屬性測試 — 回退策略按 rrf_score 降序排列
# Feature: langchain-provider-integration, Property 9: 回退策略按 rrf_score 排序
# Validates: Requirements 4.5
# ===========================================================================

@settings(max_examples=100, deadline=None)
@given(
    rrf_scores=st.lists(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False), min_size=1, max_size=30),
    top_k=st.integers(min_value=1, max_value=30),
)
def test_fallback_sorted_by_rrf_score(rrf_scores: List[float], top_k: int):
    """
    # Feature: langchain-provider-integration, Property 9: 回退策略按 rrf_score 排序
    **Validates: Requirements 4.5**

    當 API 重試耗盡後，回傳的文件列表應按 rrf_score 欄位降序排列，且數量不超過 top_k。
    """
    from tenacity import RetryError

    docs = _make_docs(len(rrf_scores), rrf_scores)

    mock_compressor = MagicMock()
    provider = _make_provider(mock_compressor=mock_compressor)

    # 直接讓 _rerank_with_retry 拋出 RetryError，跳過實際等待
    with patch.object(provider, "_rerank_with_retry", side_effect=RetryError(None)):
        result = provider.rerank("query", docs, top_k)

    # 數量不超過 top_k
    assert len(result) <= top_k

    # 按 rrf_score 降序排列
    result_scores = [d.get("rrf_score", 0) for d in result]
    assert result_scores == sorted(result_scores, reverse=True), (
        f"結果未按 rrf_score 降序排列: {result_scores}"
    )

    # 結果是原始 docs 的子集（以 id 識別）
    original_ids = {d["id"] for d in docs}
    for d in result:
        assert d["id"] in original_ids


# ===========================================================================
# Sub-task 5.2：單元測試
# ===========================================================================

class TestRerankEmptyDocs:
    """需求 4.3：docs 為空時回傳空列表"""

    def test_rerank_empty_docs_returns_empty(self):
        provider = _make_provider()
        result = provider.rerank("query", [], top_k=5)
        assert result == []


class TestRetryCount:
    """需求 4.4：重試恰好 3 次後回退（不拋出例外）"""

    def test_retry_count_on_api_failure(self):
        mock_compressor = MagicMock()
        mock_compressor.compress_documents.side_effect = RuntimeError("API error")

        provider = _make_provider(mock_compressor=mock_compressor)
        docs = _make_docs(3)

        # 應回退而非拋出例外
        result = provider.rerank("query", docs, top_k=2)

        # 重試恰好 3 次
        assert mock_compressor.compress_documents.call_count == 3

        # 回退結果：按 rrf_score 降序，不超過 top_k
        assert len(result) <= 2
        result_scores = [d.get("rrf_score", 0) for d in result]
        assert result_scores == sorted(result_scores, reverse=True)


class TestApiKeyMissing:
    """需求 4.1 / 設定錯誤：缺少 API 金鑰時拋出 ProviderConfigError"""

    def test_cohere_missing_api_key_raises_config_error(self, monkeypatch):
        monkeypatch.delenv("COHERE_API_KEY", raising=False)
        config = ProviderConfig(provider_type="cohere", api_key=None)
        with pytest.raises(ProviderConfigError, match="COHERE_API_KEY"):
            LangChainRerankingProvider(config)

    def test_cohere_env_var_accepted(self, monkeypatch):
        monkeypatch.setenv("COHERE_API_KEY", "env-key")
        mock_compressor = MagicMock()
        with patch.object(LangChainRerankingProvider, "_init_cohere", return_value=mock_compressor):
            config = ProviderConfig(provider_type="cohere", api_key=None)
            provider = LangChainRerankingProvider(config)
        assert provider._compressor is mock_compressor


class TestUnsupportedBackend:
    """不支援的 provider_type 應拋出 ProviderConfigError"""

    def test_unsupported_provider_type_raises(self):
        config = ProviderConfig(provider_type="openai", api_key="key")
        with pytest.raises(ProviderConfigError):
            LangChainRerankingProvider(config)


class TestSuccessfulRerank:
    """正常重排序流程"""

    def test_rerank_returns_docs_from_compressor(self):
        docs = _make_docs(3)

        # mock compressor 回傳 LangChain Document 物件
        try:
            from langchain_core.documents import Document
        except ImportError:
            try:
                from langchain.schema import Document  # type: ignore
            except ImportError:
                from dataclasses import dataclass, field as dc_field

                @dataclass
                class Document:  # type: ignore[no-redef]
                    page_content: str = ""
                    metadata: dict = dc_field(default_factory=dict)

        mock_compressor = MagicMock()
        # 回傳前兩筆（模擬 rerank 結果）
        mock_compressor.compress_documents.return_value = [
            Document(page_content=docs[2]["content"], metadata=docs[2]),
            Document(page_content=docs[0]["content"], metadata=docs[0]),
        ]

        provider = _make_provider(mock_compressor=mock_compressor)
        result = provider.rerank("query", docs, top_k=2)

        assert len(result) == 2
        assert result[0]["id"] == "doc_2"
        assert result[1]["id"] == "doc_0"


class TestWarningOnFallback:
    """需求 9.3：回退時以 WARNING 等級記錄"""

    def test_warning_logged_on_fallback(self, caplog):
        mock_compressor = MagicMock()
        mock_compressor.compress_documents.side_effect = RuntimeError("API error")

        provider = _make_provider(mock_compressor=mock_compressor)
        docs = _make_docs(3)

        with caplog.at_level(logging.WARNING, logger="providers.langchain_providers"):
            provider.rerank("query", docs, top_k=2)

        warning_msgs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_msgs) >= 1
