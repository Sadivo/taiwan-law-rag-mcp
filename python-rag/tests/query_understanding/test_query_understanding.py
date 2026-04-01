"""
Tests for QueryUnderstanding — Properties 8, 9 (PBT) + integration tests
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from unittest.mock import MagicMock
from hypothesis import given, settings, strategies as st

from retrieval.query_classifier import QueryClassifier, IntentType
from retrieval.query_rewriter import LanguageDetector, QueryRewriter, RewrittenQuery
from retrieval.context_manager import ContextManager, ConversationTurn
from retrieval.query_understanding import QueryUnderstanding


def make_qu(provider=None):
    return QueryUnderstanding(
        classifier=QueryClassifier(),
        rewriter=QueryRewriter(generation_provider=provider),
        context_manager=ContextManager(),
        language_detector=LanguageDetector(),
    )


def make_failing_component():
    m = MagicMock()
    m.detect.side_effect = RuntimeError("boom")
    m.classify.side_effect = RuntimeError("boom")
    m.rewrite.side_effect = RuntimeError("boom")
    m.translate.side_effect = RuntimeError("boom")
    m.expand_with_context.side_effect = RuntimeError("boom")
    return m


# ---------------------------------------------------------------------------
# Property 8: QueryUnderstanding 例外隔離
# ---------------------------------------------------------------------------

@given(query=st.text(min_size=1, max_size=200))
@settings(max_examples=100)
def test_property8_exception_isolation(query):
    """Property 8: 任何子模組拋出例外時，process() 不向上傳播"""
    failing = make_failing_component()
    qu = QueryUnderstanding(
        classifier=failing,
        rewriter=failing,
        context_manager=failing,
        language_detector=failing,
    )
    try:
        result = qu.process(query)
        assert result is not None
        assert result.expanded_query  # non-empty
    except Exception as exc:
        pytest.fail(f"process() raised an exception: {exc}")


# ---------------------------------------------------------------------------
# Property 9: expanded_query 非空
# ---------------------------------------------------------------------------

@given(query=st.text(min_size=1, max_size=200))
@settings(max_examples=100)
def test_property9_expanded_query_nonempty(query):
    """Property 9: 任意非空查詢，expanded_query 必須非空"""
    qu = make_qu()
    result = qu.process(query)
    assert result.expanded_query, f"expanded_query is empty for query: {query!r}"


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

def test_full_flow_chinese_semantic():
    qu = make_qu()
    result = qu.process("加班費計算標準")
    assert result.original == "加班費計算標準"
    assert result.language == 'zh'
    assert result.was_translated is False
    assert result.intent in (IntentType.SEMANTIC, IntentType.PROCEDURE)
    assert result.expanded_query


def test_full_flow_exact_intent():
    qu = make_qu()
    result = qu.process("勞基法第38條")
    assert result.intent == IntentType.EXACT
    assert result.law_name == "勞基法"
    assert result.was_rewritten is False
    assert result.rewritten == "勞基法第38條"


def test_full_flow_english_no_provider():
    """英文查詢，無 LLM provider → 翻譯失敗，使用原始英文查詢繼續"""
    qu = make_qu(provider=None)
    result = qu.process("how to calculate overtime pay")
    assert result.language == 'en'
    assert result.was_translated is False
    assert result.expanded_query


def test_full_flow_english_with_provider():
    provider = MagicMock()
    provider.generate.return_value = "加班費計算方式"
    qu = make_qu(provider=provider)
    result = qu.process("how to calculate overtime pay")
    assert result.language == 'en'
    assert result.was_translated is True
    assert result.expanded_query


def test_full_flow_with_session_context():
    qu = make_qu()
    sid = qu._context_manager.create_session()
    # First turn
    qu._context_manager.add_turn(sid, ConversationTurn(query="勞基法加班費", response="..."))
    # Second turn with pronoun
    result = qu.process("那第二條呢", session_id=sid)
    assert "勞基法加班費" in result.expanded_query
    assert "那第二條呢" in result.expanded_query


def test_full_flow_no_session():
    qu = make_qu()
    result = qu.process("加班費怎麼算", session_id=None)
    assert result.expanded_query == result.rewritten


def test_fallback_on_classifier_failure():
    qu = QueryUnderstanding(
        classifier=make_failing_component(),
        rewriter=QueryRewriter(),
        context_manager=ContextManager(),
        language_detector=LanguageDetector(),
    )
    result = qu.process("加班費怎麼算")
    assert result.original == "加班費怎麼算"
    assert result.expanded_query == "加班費怎麼算"
    assert result.intent == IntentType.SEMANTIC


def test_original_always_preserved():
    qu = make_qu()
    q = "勞基法第38條加班費計算"
    result = qu.process(q)
    assert result.original == q
