"""
tests/test_langchain_embedding_provider.py
Task 4 測試：LangChainEmbeddingProvider 屬性測試與單元測試
"""
from __future__ import annotations

import logging
import math
import os
from typing import List
from unittest.mock import MagicMock, patch, call

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

from providers.config import ProviderConfig, ProviderAPIError, ProviderConfigError
from providers.langchain_providers import LangChainEmbeddingProvider


# ---------------------------------------------------------------------------
# 輔助：建立帶有 mock LangChain embedder 的 provider
# ---------------------------------------------------------------------------

def _make_provider(
    provider_type: str = "openai",
    model_name: str | None = None,
    api_key: str = "test-key",
    batch_size: int = 10,
    mock_embedder: MagicMock | None = None,
) -> LangChainEmbeddingProvider:
    """建立 LangChainEmbeddingProvider，並注入 mock _lc_embedder"""
    config = ProviderConfig(
        provider_type=provider_type,
        model_name=model_name,
        api_key=api_key,
        batch_size=batch_size,
    )
    with patch.object(LangChainEmbeddingProvider, "_init_openai", return_value=mock_embedder or MagicMock()), \
         patch.object(LangChainEmbeddingProvider, "_init_cohere", return_value=mock_embedder or MagicMock()), \
         patch.object(LangChainEmbeddingProvider, "_init_huggingface", return_value=mock_embedder or MagicMock()):
        provider = LangChainEmbeddingProvider(config)
    if mock_embedder is not None:
        provider._lc_embedder = mock_embedder
    return provider


def _make_mock_embedder(dim: int = 8) -> MagicMock:
    mock = MagicMock()
    mock.embed_query.side_effect = lambda text: [float(i) for i in range(dim)]
    mock.embed_documents.side_effect = lambda texts: [[float(i) for i in range(dim)] for _ in texts]
    return mock


# ===========================================================================
# Sub-task 4.1：屬性測試 — embed_documents 批次呼叫次數符合 batch_size 限制
# Feature: langchain-provider-integration, Property 4: embed_documents 批次呼叫次數符合 batch_size 限制
# Validates: Requirements 3.3
# ===========================================================================

@settings(max_examples=100)
@given(
    n_texts=st.integers(min_value=0, max_value=200),
    batch_size=st.integers(min_value=1, max_value=50),
)
def test_batch_call_count(n_texts: int, batch_size: int):
    """
    # Feature: langchain-provider-integration, Property 4: embed_documents 批次呼叫次數符合 batch_size 限制
    **Validates: Requirements 3.3**

    對任意長度 N 的文字列表與批次大小 B，底層 API 呼叫次數應等於 ceil(N / B)，
    且每次呼叫傳入的文字數量不超過 B。
    """
    dim = 4
    mock_embedder = _make_mock_embedder(dim)
    provider = _make_provider(batch_size=batch_size, mock_embedder=mock_embedder)

    texts = [f"text_{i}" for i in range(n_texts)]
    results = provider.embed_documents(texts)

    expected_calls = math.ceil(n_texts / batch_size) if n_texts > 0 else 0
    assert mock_embedder.embed_documents.call_count == expected_calls, (
        f"n_texts={n_texts}, batch_size={batch_size}: "
        f"expected {expected_calls} calls, got {mock_embedder.embed_documents.call_count}"
    )

    # 每次呼叫傳入的文字數量不超過 batch_size
    for c in mock_embedder.embed_documents.call_args_list:
        batch_passed = c.args[0] if c.args else c.kwargs.get("texts", [])
        assert len(batch_passed) <= batch_size

    # 回傳長度等於輸入長度
    assert len(results) == n_texts


# ===========================================================================
# Sub-task 4.2：單元測試
# ===========================================================================

class TestLangChainEmbeddingProviderBackends:
    """需求 3.1：支援 openai / cohere / huggingface 後端"""

    def test_openai_backend_created_successfully(self):
        mock_lc = MagicMock()
        with patch("providers.langchain_providers.LangChainEmbeddingProvider._init_openai", return_value=mock_lc):
            config = ProviderConfig(provider_type="openai", api_key="sk-test", batch_size=10)
            provider = LangChainEmbeddingProvider(config)
        assert provider._lc_embedder is mock_lc
        assert provider._provider_type == "openai"

    def test_cohere_backend_created_successfully(self):
        mock_lc = MagicMock()
        with patch("providers.langchain_providers.LangChainEmbeddingProvider._init_cohere", return_value=mock_lc):
            config = ProviderConfig(provider_type="cohere", api_key="co-test", batch_size=10)
            provider = LangChainEmbeddingProvider(config)
        assert provider._lc_embedder is mock_lc
        assert provider._provider_type == "cohere"

    def test_huggingface_backend_created_successfully(self):
        mock_lc = MagicMock()
        with patch("providers.langchain_providers.LangChainEmbeddingProvider._init_huggingface", return_value=mock_lc):
            config = ProviderConfig(provider_type="huggingface", batch_size=10)
            provider = LangChainEmbeddingProvider(config)
        assert provider._lc_embedder is mock_lc
        assert provider._provider_type == "huggingface"


class TestApiKeyMissing:
    """需求 3.6：API 金鑰未設定時拋出 ProviderConfigError"""

    def test_openai_missing_api_key_raises_config_error(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        config = ProviderConfig(provider_type="openai", api_key=None)
        with pytest.raises(ProviderConfigError, match="OPENAI_API_KEY"):
            LangChainEmbeddingProvider(config)

    def test_cohere_missing_api_key_raises_config_error(self, monkeypatch):
        monkeypatch.delenv("COHERE_API_KEY", raising=False)
        config = ProviderConfig(provider_type="cohere", api_key=None)
        with pytest.raises(ProviderConfigError, match="COHERE_API_KEY"):
            LangChainEmbeddingProvider(config)

    def test_openai_env_var_accepted(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        mock_lc = MagicMock()
        with patch("providers.langchain_providers.LangChainEmbeddingProvider._init_openai", return_value=mock_lc):
            config = ProviderConfig(provider_type="openai", api_key=None)
            provider = LangChainEmbeddingProvider(config)
        assert provider._lc_embedder is mock_lc

    def test_huggingface_no_api_key_required(self):
        mock_lc = MagicMock()
        with patch("providers.langchain_providers.LangChainEmbeddingProvider._init_huggingface", return_value=mock_lc):
            config = ProviderConfig(provider_type="huggingface")
            provider = LangChainEmbeddingProvider(config)
        assert provider._lc_embedder is mock_lc


class TestRetryLogic:
    """需求 3.4：重試恰好 3 次"""

    def test_embed_query_retries_3_times_then_raises(self):
        mock_lc = MagicMock()
        mock_lc.embed_query.side_effect = RuntimeError("API error")
        provider = _make_provider(mock_embedder=mock_lc)

        with pytest.raises(ProviderAPIError):
            provider.embed_query("test")

        assert mock_lc.embed_query.call_count == 3

    def test_embed_documents_retries_3_times_then_raises(self):
        mock_lc = MagicMock()
        mock_lc.embed_documents.side_effect = RuntimeError("API error")
        provider = _make_provider(batch_size=5, mock_embedder=mock_lc)

        with pytest.raises(ProviderAPIError):
            provider.embed_documents(["a", "b"])

        assert mock_lc.embed_documents.call_count == 3

    def test_embed_query_succeeds_after_retry(self):
        mock_lc = MagicMock()
        dim = 4
        mock_lc.embed_query.side_effect = [
            RuntimeError("fail 1"),
            [float(i) for i in range(dim)],
        ]
        provider = _make_provider(mock_embedder=mock_lc)

        result = provider.embed_query("test")
        assert mock_lc.embed_query.call_count == 2
        assert result.shape == (dim,)


class TestWarningOnRetry:
    """需求 9.3：重試時以 WARNING 等級記錄"""

    def test_warning_logged_on_embed_query_retry(self, caplog):
        mock_lc = MagicMock()
        mock_lc.embed_query.side_effect = [
            RuntimeError("fail"),
            [1.0, 2.0, 3.0],
        ]
        provider = _make_provider(mock_embedder=mock_lc)

        with caplog.at_level(logging.WARNING, logger="providers.langchain_providers"):
            provider.embed_query("test")

        warning_msgs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_msgs) >= 1
        assert any("重試" in r.message or "Retry" in r.message for r in warning_msgs)

    def test_warning_logged_on_embed_documents_retry(self, caplog):
        mock_lc = MagicMock()
        mock_lc.embed_documents.side_effect = [
            RuntimeError("fail"),
            [[1.0, 2.0]],
        ]
        provider = _make_provider(batch_size=5, mock_embedder=mock_lc)

        with caplog.at_level(logging.WARNING, logger="providers.langchain_providers"):
            provider.embed_documents(["text"])

        warning_msgs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_msgs) >= 1


class TestEmbeddingDim:
    """embedding_dim 屬性回傳正確維度"""

    def test_openai_small_model_dim(self):
        provider = _make_provider(provider_type="openai", model_name="text-embedding-3-small")
        assert provider.embedding_dim == 1536

    def test_openai_large_model_dim(self):
        provider = _make_provider(provider_type="openai", model_name="text-embedding-3-large")
        assert provider.embedding_dim == 3072

    def test_cohere_model_dim(self):
        provider = _make_provider(provider_type="cohere", model_name="embed-multilingual-v3.0")
        assert provider.embedding_dim == 1024

    def test_huggingface_dim_from_embed_query(self):
        dim = 384
        mock_lc = _make_mock_embedder(dim)
        provider = _make_provider(provider_type="huggingface", mock_embedder=mock_lc)
        assert provider.embedding_dim == dim


class TestEmbedDocumentsBatching:
    """embed_documents 分批行為"""

    def test_results_length_matches_input(self):
        dim = 4
        mock_lc = _make_mock_embedder(dim)
        provider = _make_provider(batch_size=3, mock_embedder=mock_lc)
        texts = [f"t{i}" for i in range(7)]
        results = provider.embed_documents(texts)
        assert len(results) == 7

    def test_empty_input_returns_empty(self):
        mock_lc = _make_mock_embedder()
        provider = _make_provider(mock_embedder=mock_lc)
        assert provider.embed_documents([]) == []
        mock_lc.embed_documents.assert_not_called()
