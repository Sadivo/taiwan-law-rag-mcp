"""
providers/factory.py
ProviderFactory：根據 ProviderConfig 或環境變數建立 Provider 實例
"""
from __future__ import annotations

import logging
import os
from typing import Tuple

from .base import EmbeddingProvider, RerankingProvider
from .config import ProviderConfig, ProviderConfigError

logger = logging.getLogger(__name__)

_SUPPORTED_EMBEDDING_TYPES = ("local", "openai", "cohere", "huggingface", "google", "mistral", "voyageai", "bedrock", "azure-openai", "<任意 LangChain Embeddings>")
_SUPPORTED_RERANKING_TYPES = ("local", "cohere", "voyageai", "flashrank", "<任意 LangChain Reranker>")


class ProviderFactory:
    """根據設定建立 EmbeddingProvider 與 RerankingProvider 實例"""

    @staticmethod
    def create_embedding_provider(config: ProviderConfig) -> EmbeddingProvider:
        """根據 config.provider_type 建立對應的 EmbeddingProvider"""
        provider_type = config.provider_type

        if provider_type == "local":
            from .local_providers import LocalEmbeddingProvider
            model_name = config.model_name or "Qwen/Qwen3-Embedding-4B"
            # local 模型的 batch_size 由 Embedder._auto_batch_size() 根據 VRAM 自動決定
            # 不傳入 batch_size，避免 EMBEDDING_BATCH_SIZE 環境變數干擾
            return LocalEmbeddingProvider(model_name=model_name)

        if provider_type in ("openai", "cohere", "huggingface", "google", "mistral", "voyageai", "bedrock", "azure-openai"):
            from .langchain_providers import LangChainEmbeddingProvider
            return LangChainEmbeddingProvider(config)

        # 允許任意 provider_type，只要 config.extra["langchain_class"] 有指定
        if config.extra.get("langchain_class"):
            from .langchain_providers import LangChainEmbeddingProvider
            return LangChainEmbeddingProvider(config)

        raise ProviderConfigError(
            f"不支援的 embedding provider_type: '{provider_type}'。\n"
            f"內建支援: local, openai, cohere, huggingface, google, mistral, voyageai, bedrock, azure-openai\n"
            f"或在 config.extra['langchain_class'] 指定任意 LangChain Embeddings class。"
        )

    @staticmethod
    def create_reranking_provider(config: ProviderConfig) -> RerankingProvider:
        """根據 config.provider_type 建立對應的 RerankingProvider"""
        provider_type = config.provider_type

        if provider_type == "local":
            from .local_providers import LocalRerankingProvider
            model_name = config.model_name or "Qwen/Qwen3-Reranker-4B"
            return LocalRerankingProvider(model_name=model_name)

        if provider_type in ("cohere", "voyageai", "flashrank"):
            from .langchain_providers import LangChainRerankingProvider
            return LangChainRerankingProvider(config)

        if config.extra.get("langchain_class"):
            from .langchain_providers import LangChainRerankingProvider
            return LangChainRerankingProvider(config)

        raise ProviderConfigError(
            f"不支援的 reranking provider_type: '{provider_type}'。\n"
            f"內建支援: local, cohere, voyageai, flashrank\n"
            f"或在 config.extra['langchain_class'] 指定任意 LangChain Reranker class。"
        )

    @classmethod
    def from_env(cls) -> Tuple[EmbeddingProvider, RerankingProvider]:
        """從環境變數讀取設定並建立 Provider 實例

        環境變數：
            EMBEDDING_PROVIDER: embedding provider 類型（預設 local）
            RERANKING_PROVIDER: reranking provider 類型（預設 local）
            PROVIDER_API_KEY: 通用 API 金鑰，適用於目前選擇的 Provider
            EMBEDDING_MODEL_NAME: 覆寫 embedding 模型名稱（選填）
            RERANKING_MODEL_NAME: 覆寫 reranking 模型名稱（選填）
            EMBEDDING_BATCH_SIZE: 批次大小（預設 100）

        向下相容：若未設定 PROVIDER_API_KEY，仍會嘗試讀取
        OPENAI_API_KEY / COHERE_API_KEY 等 Provider 專屬金鑰。
        """
        embedding_provider_type = os.environ.get("EMBEDDING_PROVIDER", "local")
        reranking_provider_type = os.environ.get("RERANKING_PROVIDER", "local")
        embedding_model_name = os.environ.get("EMBEDDING_MODEL_NAME")
        reranking_model_name = os.environ.get("RERANKING_MODEL_NAME")
        batch_size_str = os.environ.get("EMBEDDING_BATCH_SIZE", "100")

        try:
            batch_size = int(batch_size_str)
        except ValueError:
            batch_size = 100

        # 通用金鑰優先，fallback 到 Provider 專屬金鑰（向下相容）
        generic_key = os.environ.get("PROVIDER_API_KEY")
        _provider_keys = {
            "openai": os.environ.get("OPENAI_API_KEY"),
            "cohere": os.environ.get("COHERE_API_KEY"),
        }

        def _resolve_key(provider_type: str) -> str | None:
            return generic_key or _provider_keys.get(provider_type)

        embedding_config = ProviderConfig(
            provider_type=embedding_provider_type,  # type: ignore[arg-type]
            model_name=embedding_model_name,
            api_key=_resolve_key(embedding_provider_type),
            batch_size=batch_size,
        )

        reranking_config = ProviderConfig(
            provider_type=reranking_provider_type,  # type: ignore[arg-type]
            model_name=reranking_model_name,
            api_key=_resolve_key(reranking_provider_type),
        )

        embedding_provider = cls.create_embedding_provider(embedding_config)
        reranking_provider = cls.create_reranking_provider(reranking_config)

        return embedding_provider, reranking_provider
