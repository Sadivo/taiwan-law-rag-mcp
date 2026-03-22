"""
tests/test_provider_factory.py
ProviderFactory 單元測試
"""
from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

# 確保 python-rag 目錄在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from providers.config import ProviderConfig, ProviderConfigError
from providers.factory import ProviderFactory
from providers.base import EmbeddingProvider, RerankingProvider


# ---------------------------------------------------------------------------
# 測試：未知 provider_type 拋出 ProviderConfigError
# ---------------------------------------------------------------------------

def test_unknown_embedding_provider_type_raises():
    """未知的 embedding provider_type 應拋出 ProviderConfigError 並列出支援類型"""
    config = ProviderConfig(provider_type="local")  # 先建立合法物件
    config.__dict__["provider_type"] = "unknown_backend"  # 繞過 Pydantic 驗證

    with pytest.raises(ProviderConfigError) as exc_info:
        ProviderFactory.create_embedding_provider(config)

    error_msg = str(exc_info.value)
    assert "unknown_backend" in error_msg
    # 應列出支援的類型
    for supported in ("local", "openai", "cohere", "huggingface"):
        assert supported in error_msg


def test_unknown_reranking_provider_type_raises():
    """未知的 reranking provider_type 應拋出 ProviderConfigError 並列出支援類型"""
    config = ProviderConfig(provider_type="local")
    config.__dict__["provider_type"] = "unknown_backend"

    with pytest.raises(ProviderConfigError) as exc_info:
        ProviderFactory.create_reranking_provider(config)

    error_msg = str(exc_info.value)
    assert "unknown_backend" in error_msg
    for supported in ("local", "cohere"):
        assert supported in error_msg


# ---------------------------------------------------------------------------
# 測試：from_env 環境變數切換 Provider
# ---------------------------------------------------------------------------

def test_env_var_embedding_provider_local():
    """EMBEDDING_PROVIDER=local 應建立 LocalEmbeddingProvider"""
    from providers.local_providers import LocalEmbeddingProvider

    mock_instance = MagicMock(spec=LocalEmbeddingProvider)

    with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "local"}, clear=False):
        with patch(
            "providers.factory.ProviderFactory.create_embedding_provider",
            return_value=mock_instance,
        ) as mock_create:
            with patch(
                "providers.factory.ProviderFactory.create_reranking_provider",
                return_value=MagicMock(spec=RerankingProvider),
            ):
                emb, _ = ProviderFactory.from_env()

    # 確認呼叫時傳入的 config 是 local 類型
    call_config: ProviderConfig = mock_create.call_args[0][0]
    assert call_config.provider_type == "local"
    assert emb is mock_instance


def test_env_var_embedding_provider_openai():
    """EMBEDDING_PROVIDER=openai 應建立 LangChainEmbeddingProvider"""
    from providers.langchain_providers import LangChainEmbeddingProvider

    mock_instance = MagicMock(spec=LangChainEmbeddingProvider)

    env = {"EMBEDDING_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=False):
        with patch(
            "providers.factory.ProviderFactory.create_embedding_provider",
            return_value=mock_instance,
        ) as mock_create:
            with patch(
                "providers.factory.ProviderFactory.create_reranking_provider",
                return_value=MagicMock(spec=RerankingProvider),
            ):
                emb, _ = ProviderFactory.from_env()

    call_config: ProviderConfig = mock_create.call_args[0][0]
    assert call_config.provider_type == "openai"
    assert call_config.api_key == "test-key"
    assert emb is mock_instance


def test_env_var_reranking_provider_local():
    """RERANKING_PROVIDER=local 應建立 LocalRerankingProvider"""
    from providers.local_providers import LocalRerankingProvider

    mock_instance = MagicMock(spec=LocalRerankingProvider)

    with patch.dict(os.environ, {"RERANKING_PROVIDER": "local"}, clear=False):
        with patch(
            "providers.factory.ProviderFactory.create_embedding_provider",
            return_value=MagicMock(spec=EmbeddingProvider),
        ):
            with patch(
                "providers.factory.ProviderFactory.create_reranking_provider",
                return_value=mock_instance,
            ) as mock_create:
                _, rnk = ProviderFactory.from_env()

    call_config: ProviderConfig = mock_create.call_args[0][0]
    assert call_config.provider_type == "local"
    assert rnk is mock_instance


def test_env_var_reranking_provider_cohere():
    """RERANKING_PROVIDER=cohere 應建立 LangChainRerankingProvider"""
    from providers.langchain_providers import LangChainRerankingProvider

    mock_instance = MagicMock(spec=LangChainRerankingProvider)

    env = {"RERANKING_PROVIDER": "cohere", "COHERE_API_KEY": "cohere-key"}
    with patch.dict(os.environ, env, clear=False):
        with patch(
            "providers.factory.ProviderFactory.create_embedding_provider",
            return_value=MagicMock(spec=EmbeddingProvider),
        ):
            with patch(
                "providers.factory.ProviderFactory.create_reranking_provider",
                return_value=mock_instance,
            ) as mock_create:
                _, rnk = ProviderFactory.from_env()

    call_config: ProviderConfig = mock_create.call_args[0][0]
    assert call_config.provider_type == "cohere"
    assert call_config.api_key == "cohere-key"
    assert rnk is mock_instance


# ---------------------------------------------------------------------------
# 測試：create_embedding_provider 直接建立（mock 底層 Provider）
# ---------------------------------------------------------------------------

def test_create_embedding_provider_local_returns_local_instance():
    """create_embedding_provider(local) 應回傳 LocalEmbeddingProvider 實例"""
    from providers.local_providers import LocalEmbeddingProvider

    mock_local = MagicMock(spec=LocalEmbeddingProvider)

    # LocalEmbeddingProvider 是在 local_providers 模組中定義的，lazy import 後從那裡 patch
    with patch("providers.local_providers.LocalEmbeddingProvider", return_value=mock_local) as MockCls:
        config = ProviderConfig(provider_type="local")
        result = ProviderFactory.create_embedding_provider(config)

    MockCls.assert_called_once()
    assert result is mock_local


def test_create_reranking_provider_local_returns_local_instance():
    """create_reranking_provider(local) 應回傳 LocalRerankingProvider 實例"""
    from providers.local_providers import LocalRerankingProvider

    mock_local = MagicMock(spec=LocalRerankingProvider)

    with patch("providers.local_providers.LocalRerankingProvider", return_value=mock_local) as MockCls:
        config = ProviderConfig(provider_type="local")
        result = ProviderFactory.create_reranking_provider(config)

    MockCls.assert_called_once()
    assert result is mock_local
