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
            EMBEDDING_API_KEY: embedding provider 專用金鑰
            RERANKING_API_KEY: reranking provider 專用金鑰
            PROVIDER_API_KEY: 通用金鑰，當 EMBEDDING_API_KEY / RERANKING_API_KEY 未設定時使用
            EMBEDDING_MODEL_NAME: 覆寫 embedding 模型名稱（選填）
            RERANKING_MODEL_NAME: 覆寫 reranking 模型名稱（選填）
            EMBEDDING_BATCH_SIZE: 批次大小（預設 100，僅影響線上 Provider）

        金鑰優先順序（以 embedding 為例）：
            EMBEDDING_API_KEY > PROVIDER_API_KEY > OPENAI_API_KEY / COHERE_API_KEY（向下相容）
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

        # 金鑰優先順序：專用金鑰 > 通用金鑰 > 舊格式向下相容
        generic_key = os.environ.get("PROVIDER_API_KEY")
        _legacy_keys = {
            "openai": os.environ.get("OPENAI_API_KEY"),
            "cohere": os.environ.get("COHERE_API_KEY"),
        }

        def _resolve_key(provider_type: str, specific_key_env: str) -> str | None:
            return (
                os.environ.get(specific_key_env)
                or generic_key
                or _legacy_keys.get(provider_type)
            )

        embedding_config = ProviderConfig(
            provider_type=embedding_provider_type,
            model_name=embedding_model_name,
            api_key=_resolve_key(embedding_provider_type, "EMBEDDING_API_KEY"),
            batch_size=batch_size,
        )

        reranking_config = ProviderConfig(
            provider_type=reranking_provider_type,
            model_name=reranking_model_name,
            api_key=_resolve_key(reranking_provider_type, "RERANKING_API_KEY"),
        )

        embedding_provider = cls.create_embedding_provider(embedding_config)
        reranking_provider = cls.create_reranking_provider(reranking_config)

        return embedding_provider, reranking_provider
