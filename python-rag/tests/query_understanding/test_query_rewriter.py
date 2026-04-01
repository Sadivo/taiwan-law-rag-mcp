"""
Tests for QueryRewriter — Properties 2, 3, 4 (PBT) + unit tests
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from unittest.mock import MagicMock, patch
from hypothesis import given, settings, strategies as st

from retrieval.query_classifier import IntentType
from retrieval.query_rewriter import QueryRewriter, RewrittenQuery

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_rewriter(provider=None):
    return QueryRewriter(generation_provider=provider, timeout=10.0, max_length=500)


def make_failing_provider(exc=Exception("LLM unavailable")):
    provider = MagicMock()
    provider.generate.side_effect = exc
    return provider


# ---------------------------------------------------------------------------
# Property 2: exact 意圖不改寫
# ---------------------------------------------------------------------------

# Queries that contain an article number pattern (exact intent)
exact_queries = st.builds(
    lambda n: f"勞基法第{n}條",
    st.integers(min_value=1, max_value=999),
)


@given(query=exact_queries)
@settings(max_examples=100)
def test_property2_exact_not_rewritten(query):
    """Property 2: exact 意圖時 rewrite() 回傳值等於輸入"""
    rewriter = make_rewriter(provider=MagicMock())
    result = rewriter.rewrite(query, IntentType.EXACT)
    assert result == query, f"Expected original for exact intent, got {result!r}"


# ---------------------------------------------------------------------------
# Property 3: original 欄位保留（Round-Trip）
# 這裡測試 rewrite() 在 no-provider 情況下的 fallback 行為
# ---------------------------------------------------------------------------

@given(query=st.text(min_size=1, max_size=500))
@settings(max_examples=100)
def test_property3_rewrite_fallback_returns_original(query):
    """Property 3: 無 provider 時 rewrite() 回傳原始查詢"""
    rewriter = make_rewriter(provider=None)
    result = rewriter.rewrite(query, IntentType.SEMANTIC)
    assert result == query


# ---------------------------------------------------------------------------
# Property 4: LLM 不可用時 fallback 不拋出例外
# ---------------------------------------------------------------------------

@given(query=st.text(min_size=1, max_size=200))
@settings(max_examples=100)
def test_property4_llm_failure_no_exception(query):
    """Property 4: LLM 拋出例外時 rewrite() 不向上傳播，回傳原始查詢"""
    rewriter = make_rewriter(provider=make_failing_provider())
    try:
        result = rewriter.rewrite(query, IntentType.SEMANTIC)
        assert result == query
    except Exception as exc:
        pytest.fail(f"rewrite() raised an exception: {exc}")


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_exact_intent_no_provider():
    rewriter = make_rewriter()
    assert rewriter.rewrite("勞基法第38條", IntentType.EXACT) == "勞基法第38條"


def test_semantic_no_provider_fallback():
    rewriter = make_rewriter()
    q = "加班費怎麼算"
    assert rewriter.rewrite(q, IntentType.SEMANTIC) == q


def test_procedure_no_provider_fallback():
    rewriter = make_rewriter()
    q = "如何申請加班費"
    assert rewriter.rewrite(q, IntentType.PROCEDURE) == q


def test_llm_rewrite_success():
    provider = MagicMock()
    provider.generate.return_value = "加班費計算 延長工時工資標準"
    rewriter = make_rewriter(provider=provider)
    result = rewriter.rewrite("加班費怎麼算", IntentType.SEMANTIC)
    assert result == "加班費計算 延長工時工資標準"


def test_llm_exception_fallback():
    rewriter = make_rewriter(provider=make_failing_provider())
    q = "加班費怎麼算"
    result = rewriter.rewrite(q, IntentType.SEMANTIC)
    assert result == q


def test_query_truncation_rewrite():
    """501 字元輸入，rewrite 使用截斷後的查詢（provider 收到 ≤500 字元）"""
    long_query = "加" * 501
    received = []

    provider = MagicMock()
    def capture(prompt):
        received.append(prompt)
        return "改寫結果"
    provider.generate.side_effect = capture

    rewriter = make_rewriter(provider=provider)
    rewriter.rewrite(long_query, IntentType.SEMANTIC)

    assert len(received) == 1
    # prompt contains the truncated query (500 chars)
    assert "加" * 500 in received[0]
    assert "加" * 501 not in received[0]


def test_translate_no_provider():
    rewriter = make_rewriter()
    assert rewriter.translate("overtime pay") is None


def test_translate_success():
    provider = MagicMock()
    provider.generate.return_value = "加班費"
    rewriter = make_rewriter(provider=provider)
    assert rewriter.translate("overtime pay") == "加班費"


def test_translate_failure_returns_none():
    rewriter = make_rewriter(provider=make_failing_provider())
    assert rewriter.translate("overtime pay") is None


def test_translate_timeout_returns_none():
    """模擬翻譯超時"""
    import concurrent.futures
    provider = MagicMock()

    def slow_generate(prompt):
        import time
        time.sleep(20)
        return "result"

    provider.generate.side_effect = slow_generate
    rewriter = QueryRewriter(generation_provider=provider, timeout=0.05)
    result = rewriter.translate("overtime pay")
    assert result is None
