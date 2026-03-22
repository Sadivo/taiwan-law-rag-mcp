"""
providers/langchain_providers.py
LangChainEmbeddingProvider 與 LangChainRerankingProvider
透過 LangChain 介面呼叫線上 Embedding / Reranking API
"""
from __future__ import annotations

import importlib
import logging
from typing import List, Dict, Any

import numpy as np

from .base import EmbeddingProvider, RerankingProvider
from .config import ProviderConfig, ProviderAPIError, ProviderConfigError

logger = logging.getLogger(__name__)

_BUILTIN_EMBEDDINGS: Dict[str, tuple] = {
    # name: (pip_package, module_path, class_name, default_model)
    "openai":       ("langchain-openai",       "langchain_openai",       "OpenAIEmbeddings",                  "text-embedding-3-small"),
    "cohere":       ("langchain-cohere",        "langchain_cohere",       "CohereEmbeddings",                  "embed-multilingual-v3.0"),
    "huggingface":  ("langchain-huggingface",   "langchain_huggingface",  "HuggingFaceEmbeddings",             "sentence-transformers/all-MiniLM-L6-v2"),
    "google":       ("langchain-google-genai",  "langchain_google_genai", "GoogleGenerativeAIEmbeddings",      "models/embedding-001"),
    "mistral":      ("langchain-mistralai",     "langchain_mistralai",    "MistralAIEmbeddings",               "mistral-embed"),
    "voyageai":     ("langchain-voyageai",      "langchain_voyageai",     "VoyageAIEmbeddings",                "voyage-3"),
    "bedrock":      ("langchain-aws",           "langchain_aws",          "BedrockEmbeddings",                 "amazon.titan-embed-text-v1"),
    "azure-openai": ("langchain-openai",        "langchain_openai",       "AzureOpenAIEmbeddings",             None),
}

_KNOWN_DIMS: Dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "embed-multilingual-v3.0": 1024,
    "embed-english-v3.0": 1024,
    "embed-multilingual-light-v3.0": 384,
    "embed-english-light-v3.0": 384,
    "mistral-embed": 1024,
    "voyage-3": 1024,
    "voyage-3-lite": 512,
    "voyage-3-large": 2048,
    "voyage-3.5": 1024,
    "voyage-3.5-lite": 512,
    "voyage-finance-2": 1024,
    "voyage-law-2": 1024,
    "voyage-code-3": 2048,
    "models/embedding-001": 768,
    "models/text-embedding-004": 768,
    "amazon.titan-embed-text-v1": 1536,
    "amazon.titan-embed-text-v2:0": 1024,
    "cohere.embed-multilingual-v3": 1024,
    "cohere.embed-english-v3": 1024,
}

_BUILTIN_RERANKERS: Dict[str, tuple] = {
    # name: (pip_package, module_path, class_name, default_model)
    "cohere":    ("langchain-cohere",   "langchain_cohere",                    "CohereRerank",    "rerank-multilingual-v3.0"),
    "voyageai":  ("langchain-voyageai", "langchain_voyageai",                  "VoyageAIRerank",  "rerank-2"),
    "flashrank": ("flashrank",          "langchain_community.document_compressors", "FlashrankRerank", None),
}

# 各 provider 的 API key 參數名 — 已不需要，key 由 factory._inject_api_key() 注入環境變數
# LangChain 各 provider 會自動從標準環境變數讀取（VOYAGE_API_KEY、OPENAI_API_KEY 等）
_API_KEY_PARAM: Dict[str, str] = {}

_RERANKER_API_KEY_PARAM: Dict[str, str] = {}


def _load_lc_class(module_path: str, class_name: str, pip_package: str):
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name)
    except ImportError as exc:
        raise ProviderConfigError(
            f"找不到 {module_path}.{class_name}，請安裝：pip install {pip_package}"
        ) from exc
    except AttributeError as exc:
        raise ProviderConfigError(
            f"{module_path} 中找不到 {class_name}，請確認套件版本"
        ) from exc


def _try_instantiate(cls, kwargs: Dict[str, Any]) -> Any:
    """嘗試實例化，失敗時拋出 ProviderConfigError。"""
    try:
        return cls(**kwargs)
    except Exception as exc:
        raise ProviderConfigError(
            f"初始化 {cls.__name__} 失敗：{exc}\n"
            f"可透過 config.extra 傳入額外參數。"
        ) from exc


class LangChainEmbeddingProvider(EmbeddingProvider):
    """透過 LangChain Embeddings 介面呼叫任意線上 Embedding API。"""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._provider_type = config.provider_type
        self._batch_size = config.batch_size
        self._embedding_dim_cache: int | None = None
        self._lc_embedder = self._init_embedder(config)
        logger.info(
            "LangChainEmbeddingProvider 初始化成功：provider_type=%s, model_name=%s",
            self._provider_type,
            config.model_name or self._default_model_name(),
        )

    def _init_embedder(self, config: ProviderConfig):
        provider_type = config.provider_type

        custom_class_path: str | None = config.extra.get("langchain_class")
        if custom_class_path:
            module_path, class_name = custom_class_path.rsplit(".", 1)
            cls = _load_lc_class(module_path, class_name, custom_class_path)
            return self._build_embedder(cls, config, key_param=None)

        if provider_type not in _BUILTIN_EMBEDDINGS:
            raise ProviderConfigError(
                f"不支援的 provider_type: '{provider_type}'。\n"
                f"內建支援: {', '.join(_BUILTIN_EMBEDDINGS)}\n"
                f"或透過 config.extra['langchain_class'] 指定任意 LangChain Embeddings class。"
            )

        pip_pkg, module_path, class_name, _ = _BUILTIN_EMBEDDINGS[provider_type]
        cls = _load_lc_class(module_path, class_name, pip_pkg)
        key_param = _API_KEY_PARAM.get(provider_type)
        return self._build_embedder(cls, config, key_param=key_param)

    def _build_embedder(self, cls, config: ProviderConfig, key_param: str | None):
        model = config.model_name or self._default_model_name()
        kwargs: Dict[str, Any] = {}

        if model:
            try:
                return self._try_with_model_key(cls, kwargs, model, config)
            except ProviderConfigError:
                raise
            except Exception:
                pass

        kwargs.update(config.extra.get("init_kwargs", {}))
        return _try_instantiate(cls, kwargs)

    def _try_with_model_key(self, cls, base_kwargs: Dict[str, Any], model: str,
                             config: ProviderConfig, key_param: str | None = None):
        """逐一嘗試 model / model_name 作為模型參數名，回傳第一個成功的實例。"""
        extra = config.extra.get("init_kwargs", {})
        last_exc = None
        for model_key in ("model", "model_name"):
            try:
                return cls(**base_kwargs, **extra, **{model_key: model})
            except Exception as exc:
                last_exc = exc
        raise ProviderConfigError(
            f"初始化 {cls.__name__} 失敗：{last_exc}\n可透過 config.extra 傳入額外參數。"
        ) from last_exc

    def _default_model_name(self) -> str:
        entry = _BUILTIN_EMBEDDINGS.get(self._provider_type)
        return entry[3] if entry else ""

    def _embed_query_with_retry(self, text: str) -> np.ndarray:
        from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type, RetryError

        @retry(stop=stop_after_attempt(3), wait=wait_fixed(1),
               retry=retry_if_exception_type(Exception),
               before_sleep=lambda rs: logger.warning("embed_query 重試 %d/3...", rs.attempt_number))
        def _call():
            return self._lc_embedder.embed_query(text)

        try:
            return np.array(_call(), dtype=np.float32)
        except RetryError as exc:
            raise ProviderAPIError(f"embed_query 重試 3 次後仍失敗：{exc}") from exc

    def _embed_batch_with_retry(self, batch: List[str]) -> List[np.ndarray]:
        from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type, RetryError

        @retry(stop=stop_after_attempt(3), wait=wait_fixed(1),
               retry=retry_if_exception_type(Exception),
               before_sleep=lambda rs: logger.warning("embed_documents 重試 %d/3...", rs.attempt_number))
        def _call():
            return self._lc_embedder.embed_documents(batch)

        try:
            return [np.array(v, dtype=np.float32) for v in _call()]
        except RetryError as exc:
            raise ProviderAPIError(f"embed_documents 重試 3 次後仍失敗：{exc}") from exc

    def embed_query(self, text: str) -> np.ndarray:
        return self._embed_query_with_retry(text)

    def embed_documents(self, texts: List[str]) -> List[np.ndarray]:
        results: List[np.ndarray] = []
        for i in range(0, len(texts), self._batch_size):
            results.extend(self._embed_batch_with_retry(texts[i:i + self._batch_size]))
        return results

    @property
    def embedding_dim(self) -> int:
        if self._embedding_dim_cache is not None:
            return self._embedding_dim_cache
        model = self._config.model_name or self._default_model_name()
        dim = _KNOWN_DIMS.get(model) if model else None
        if dim is None:
            dim = int(self.embed_query("dim").shape[0])
        self._embedding_dim_cache = dim
        return self._embedding_dim_cache


class LangChainRerankingProvider(RerankingProvider):
    """透過 LangChain BaseDocumentCompressor 介面呼叫任意線上 Reranking API。"""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._provider_type = config.provider_type
        self._compressor = self._init_compressor(config)
        entry = _BUILTIN_RERANKERS.get(self._provider_type)
        logger.info(
            "LangChainRerankingProvider 初始化成功：provider_type=%s, model_name=%s",
            self._provider_type,
            config.model_name or (entry[3] if entry else ""),
        )

    def _init_compressor(self, config: ProviderConfig):
        provider_type = config.provider_type

        custom_class_path: str | None = config.extra.get("langchain_class")
        if custom_class_path:
            module_path, class_name = custom_class_path.rsplit(".", 1)
            cls = _load_lc_class(module_path, class_name, custom_class_path)
            return self._build_compressor(cls, config, key_param=None)

        if provider_type not in _BUILTIN_RERANKERS:
            raise ProviderConfigError(
                f"不支援的 provider_type: '{provider_type}'。\n"
                f"內建支援: {', '.join(_BUILTIN_RERANKERS)}\n"
                f"或透過 config.extra['langchain_class'] 指定任意 LangChain Reranker class。"
            )

        pip_pkg, module_path, class_name, _ = _BUILTIN_RERANKERS[provider_type]
        cls = _load_lc_class(module_path, class_name, pip_pkg)
        key_param = _RERANKER_API_KEY_PARAM.get(provider_type)
        return self._build_compressor(cls, config, key_param=key_param)

    def _build_compressor(self, cls, config: ProviderConfig, key_param: str | None):
        entry = _BUILTIN_RERANKERS.get(self._provider_type)
        model = config.model_name or (entry[3] if entry else None)
        extra = config.extra.get("init_kwargs", {})
        last_exc = None
        for model_key in (["model"] if model else []) + [None]:
            try:
                kwargs = {**extra}
                if model_key:
                    kwargs[model_key] = model
                return cls(**kwargs)
            except Exception as exc:
                last_exc = exc

        raise ProviderConfigError(
            f"初始化 {cls.__name__} 失敗：{last_exc}\n可透過 config.extra 傳入額外參數。"
        ) from last_exc

    def _rerank_with_retry(self, query: str, lc_docs: List[Any]) -> List[Any]:
        from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type, RetryError

        @retry(stop=stop_after_attempt(3), wait=wait_fixed(1),
               retry=retry_if_exception_type(Exception),
               before_sleep=lambda rs: logger.warning("rerank 重試 %d/3...", rs.attempt_number))
        def _call():
            return self._compressor.compress_documents(lc_docs, query)

        try:
            return _call()
        except RetryError as exc:
            raise ProviderAPIError(f"rerank 重試 3 次後仍失敗：{exc}") from exc

    def rerank(self, query: str, docs: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        if not docs:
            return []

        try:
            from langchain_core.documents import Document
        except ImportError:
            from langchain.schema import Document  # type: ignore

        lc_docs = [Document(page_content=doc.get("content", ""), metadata=doc) for doc in docs]

        try:
            results = self._rerank_with_retry(query, lc_docs)
            return [doc.metadata for doc in results]
        except ProviderAPIError:
            logger.warning("rerank 重試耗盡，回退至 rrf_score 排序")
            return sorted(docs, key=lambda d: d.get("rrf_score", 0), reverse=True)[:top_k]
