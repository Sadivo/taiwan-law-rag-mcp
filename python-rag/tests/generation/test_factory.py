"""
tests/generation/test_factory.py
Property 5: 不支援的 provider 類型拋出 ProviderConfigError

Feature: rag-generation, Property 5: 不支援的 provider 類型拋出 ProviderConfigError
Validates: Requirements 3.3
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from providers.config import ProviderConfig, ProviderConfigError
from providers.factory import ProviderFactory

_SUPPORTED = {"ollama", "openai", "anthropic"}


@given(st.text().filter(lambda s: s not in _SUPPORTED))
@settings(max_examples=100)
def test_property5_unsupported_provider_raises_config_error(provider_type: str):
    """
    Property 5: 不支援的 provider 類型拋出 ProviderConfigError
    Validates: Requirements 3.3
    """
    config = ProviderConfig(provider_type=provider_type)

    with pytest.raises(ProviderConfigError) as exc_info:
        ProviderFactory.create_generation_provider(config)

    error_message = str(exc_info.value)
    # 訊息應列出支援的選項
    for supported in _SUPPORTED:
        assert supported in error_message, (
            f"ProviderConfigError 訊息應包含支援的 provider '{supported}'，"
            f"但實際訊息為：{error_message!r}"
        )
