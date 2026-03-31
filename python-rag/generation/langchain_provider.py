"""
generation/langchain_provider.py
LangChainGenerationProvider — 透過 LangChain BaseChatModel 統一支援多個 LLM 後端
"""
from __future__ import annotations

import importlib
import logging
import os
from typing import Iterator

from providers.config import ProviderConfig
from .base import GenerationProvider, GenerationProviderError

logger = logging.getLogger(__name__)

# (pip_package, module_path, class_name, default_model)
_BUILTIN_CHAT_MODELS: dict[str, tuple] = {
    "ollama":    ("langchain-ollama",    "langchain_ollama",    "ChatOllama",    "qwen3:8b"),
    "openai":    ("langchain-openai",    "langchain_openai",    "ChatOpenAI",    "gpt-4o-mini"),
    "anthropic": ("langchain-anthropic", "langchain_anthropic", "ChatAnthropic", "claude-3-5-haiku-20241022"),
}

# provider 對應需注入的環境變數
_PROVIDER_ENV_KEY: dict[str, str | None] = {
    "ollama":    None,
    "openai":    "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def _load_lc_class(module_path: str, class_name: str, pip_package: str):
    """動態載入 LangChain class，失敗時拋出 GenerationProviderError。"""
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name)
    except ImportError as exc:
        raise GenerationProviderError(
            f"找不到 {module_path}.{class_name}，請安裝：pip install {pip_package}"
        ) from exc
    except AttributeError as exc:
        raise GenerationProviderError(
            f"{module_path} 中找不到 {class_name}，請確認套件版本"
        ) from exc


class LangChainGenerationProvider(GenerationProvider):
    """透過 LangChain BaseChatModel 介面呼叫任意 LLM 後端。"""

    def __init__(self, config: ProviderConfig) -> None:
        self._provider_type = config.provider_type
        self._llm = self._init_llm(config)
        logger.info(
            "LangChainGenerationProvider 初始化成功：provider_name=%s",
            self.provider_name,
        )

    def _init_llm(self, config: ProviderConfig):
        ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        max_tokens = config.extra.get("max_tokens", 1024)

        # 自訂 class 優先
        custom_class_path: str | None = config.extra.get("langchain_class")
        if custom_class_path:
            module_path, class_name = custom_class_path.rsplit(".", 1)
            cls = _load_lc_class(module_path, class_name, custom_class_path)
            model_name = config.model_name or ""
            kwargs = config.extra.get("init_kwargs", {})
            if model_name:
                kwargs = {"model": model_name, **kwargs}
            self._model_name = model_name
            return cls(**kwargs)

        provider_type = config.provider_type
        if provider_type not in _BUILTIN_CHAT_MODELS:
            raise GenerationProviderError(
                f"不支援的 provider_type: '{provider_type}'。\n"
                f"內建支援: {', '.join(_BUILTIN_CHAT_MODELS)}\n"
                f"或透過 config.extra['langchain_class'] 指定任意 LangChain BaseChatModel class。"
            )

        pip_pkg, module_path, class_name, default_model = _BUILTIN_CHAT_MODELS[provider_type]
        model_name = config.model_name or default_model
        self._model_name = model_name

        # openai / anthropic 需要 API key
        if provider_type in ("openai", "anthropic"):
            api_key = os.environ.get("GENERATION_API_KEY")
            if not api_key:
                raise GenerationProviderError(
                    f"使用 {provider_type} 需要設定 GENERATION_API_KEY 環境變數。"
                )
            env_var = _PROVIDER_ENV_KEY[provider_type]
            if env_var and not os.environ.get(env_var):
                os.environ[env_var] = api_key

        cls = _load_lc_class(module_path, class_name, pip_pkg)

        if provider_type == "ollama":
            return cls(base_url=ollama_base_url, model=model_name, num_predict=max_tokens)
        else:
            return cls(model=model_name)

    def generate(self, prompt: str) -> str:
        """呼叫 LLM 並回傳生成文字。"""
        try:
            from langchain_core.messages import HumanMessage
        except ImportError:
            from langchain.schema import HumanMessage  # type: ignore

        result = self._llm.invoke([HumanMessage(content=prompt)])
        return result.content

    def generate_stream(self, prompt: str) -> Iterator[str]:
        """以迭代器方式逐 token 回傳生成文字。"""
        try:
            from langchain_core.messages import HumanMessage
        except ImportError:
            from langchain.schema import HumanMessage  # type: ignore

        for chunk in self._llm.stream([HumanMessage(content=prompt)]):
            yield chunk.content

    @property
    def provider_name(self) -> str:
        return f"{self._provider_type}:{self._model_name}"
