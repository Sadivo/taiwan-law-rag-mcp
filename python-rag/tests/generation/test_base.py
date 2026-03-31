"""
tests/generation/test_base.py
Property 1: 未完整實作的子類別無法實例化
Validates: Requirements 1.4
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from generation.base import GenerationProvider


# ---------------------------------------------------------------------------
# Property 1: 未完整實作的子類別無法實例化
# ---------------------------------------------------------------------------

@given(st.just(None))
@settings(max_examples=100)
def test_incomplete_subclass_cannot_instantiate(_):
    """
    Feature: rag-generation, Property 1: 未完整實作的子類別無法實例化
    Validates: Requirements 1.4

    未實作任何抽象方法的子類別在實例化時應拋出 TypeError。
    """
    class IncompleteProvider(GenerationProvider):
        pass

    with pytest.raises(TypeError):
        IncompleteProvider()


@given(st.just(None))
@settings(max_examples=100)
def test_partial_subclass_missing_generate_stream_cannot_instantiate(_):
    """
    Property 1 (partial): 只實作 generate 但缺少 generate_stream 與 provider_name 的子類別無法實例化
    Validates: Requirements 1.4
    """
    class PartialProvider(GenerationProvider):
        def generate(self, prompt: str) -> str:
            return ""

    with pytest.raises(TypeError):
        PartialProvider()


@given(st.just(None))
@settings(max_examples=100)
def test_full_subclass_can_instantiate(_):
    """
    Property 1 (inverse): 完整實作所有抽象方法的子類別可以正常實例化
    Validates: Requirements 1.4
    """
    class FullProvider(GenerationProvider):
        def generate(self, prompt: str) -> str:
            return "result"

        def generate_stream(self, prompt: str):
            yield "token"

        @property
        def provider_name(self) -> str:
            return "test:model"

    provider = FullProvider()
    assert provider is not None
