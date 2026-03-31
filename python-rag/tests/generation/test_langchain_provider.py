"""
tests/generation/test_langchain_provider.py
Properties 2, 3, 4 for LangChainGenerationProvider
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from generation.base import GenerationProviderError
from generation.langchain_provider import LangChainGenerationProvider
from providers.config import ProviderConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_llm() -> MagicMock:
    mock = MagicMock()
    mock.invoke.return_value = MagicMock(content="test response")
    mock.stream.return_value = iter([MagicMock(content="token")])
    return mock


def _make_config(provider_type: str, extra: dict | None = None) -> ProviderConfig:
    return ProviderConfig(provider_type=provider_type, extra=extra or {})


# ---------------------------------------------------------------------------
# Property 2: 支援的 provider 類型均可正確初始化
# Validates: Requirements 2.2, 2.3, 2.4
# ---------------------------------------------------------------------------

@given(st.sampled_from(["ollama", "openai", "anthropic"]))
@settings(max_examples=100)
def test_supported_providers_initialize_correctly(provider_type: str):
    """
    Feature: rag-generation, Property 2: 支援的 provider 類型均可正確初始化
    Validates: Requirements 2.2, 2.3, 2.4

    對任意支援的 provider 類型，LangChainGenerationProvider 應能正確初始化，
    且 provider_name 包含 provider type。
    """
    mock_llm = _make_mock_llm()
    config = _make_config(provider_type)

    env_patch = {}
    if provider_type in ("openai", "anthropic"):
        env_patch["GENERATION_API_KEY"] = "test-api-key"

    with patch.dict(os.environ, env_patch, clear=False), \
         patch("generation.langchain_provider._load_lc_class", return_value=lambda **kwargs: mock_llm):
        provider = LangChainGenerationProvider(config)

    assert provider_type in provider.provider_name


# ---------------------------------------------------------------------------
# Property 3: 動態載入任意 LangChain chat model class
# Validates: Requirements 2.5
# ---------------------------------------------------------------------------

@given(
    module_name=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"),
        min_size=1,
    ).filter(lambda s: s[0].isalpha()),
    class_name=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"),
        min_size=1,
    ).filter(lambda s: s[0].isalpha()),
)
@settings(max_examples=100)
def test_dynamic_class_loading(module_name: str, class_name: str):
    """
    Feature: rag-generation, Property 3: 動態載入任意 LangChain chat model class
    Validates: Requirements 2.5

    當 config.extra['langchain_class'] 設定時，應動態載入指定的 BaseChatModel 子類別。
    """
    mock_llm = _make_mock_llm()
    mock_cls = MagicMock(return_value=mock_llm)
    langchain_class_path = f"{module_name}.{class_name}"

    config = _make_config("custom", extra={"langchain_class": langchain_class_path})

    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock()
        setattr(mock_module, class_name, mock_cls)
        mock_import.return_value = mock_module

        provider = LangChainGenerationProvider(config)

    mock_import.assert_called_once_with(module_name)
    assert provider._llm is mock_llm


# ---------------------------------------------------------------------------
# Property 4: 缺少 API 金鑰時拋出 GenerationProviderError
# Validates: Requirements 2.6
# ---------------------------------------------------------------------------

@given(st.sampled_from(["openai", "anthropic"]))
@settings(max_examples=100)
def test_missing_api_key_raises_error(provider_type: str):
    """
    Feature: rag-generation, Property 4: 缺少 API 金鑰時拋出 GenerationProviderError
    Validates: Requirements 2.6

    對需要 API 金鑰的 provider（openai、anthropic），未設定 GENERATION_API_KEY 時
    應拋出 GenerationProviderError。
    """
    config = _make_config(provider_type)

    env_without_key = {k: v for k, v in os.environ.items()
                       if k not in ("GENERATION_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")}

    with patch.dict(os.environ, env_without_key, clear=True):
        with pytest.raises(GenerationProviderError):
            LangChainGenerationProvider(config)
