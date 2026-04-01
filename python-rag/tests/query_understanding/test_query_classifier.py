"""
Tests for QueryClassifier — Property 1 (PBT) + unit tests
"""
import pytest
from hypothesis import given, settings, strategies as st

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from retrieval.query_classifier import QueryClassifier, IntentType, ClassificationResult

classifier = QueryClassifier()


# ---------------------------------------------------------------------------
# Property 1: 意圖分類優先順序不變性
# 含條號的查詢，無論同時含有哪些其他關鍵字，結果必為 exact
# ---------------------------------------------------------------------------

# 生成含條號的查詢（模式1：第X條）
exact_suffix = st.builds(
    lambda n: f"第{n}條",
    st.integers(min_value=1, max_value=999),
)

# 其他模式的前綴關鍵字
other_keywords = st.sampled_from([
    "比較", "差異", "什麼是", "定義", "如何", "步驟", "流程", "怎麼辦",
    "何謂", "程序", "怎麼", "vs",
])


@given(
    prefix=other_keywords,
    article=exact_suffix,
)
@settings(max_examples=100)
def test_property1_exact_priority(prefix, article):
    """Property 1: 含條號的查詢，結果必為 exact，不論是否同時含其他模式關鍵字"""
    query = f"{prefix}勞基法{article}"
    result = classifier.classify(query)
    assert result.intent == IntentType.EXACT, (
        f"Expected EXACT for {query!r}, got {result.intent}"
    )


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("query,expected_intent", [
    ("加班費怎麼算", IntentType.PROCEDURE),
    ("加班費如何計算", IntentType.PROCEDURE),
    ("什麼是勞動契約", IntentType.DEFINITION),
    ("勞動契約的定義", IntentType.DEFINITION),
    ("何謂強制執行", IntentType.DEFINITION),
    ("勞基法和民法的差異", IntentType.COMPARISON),
    ("比較勞基法和公司法", IntentType.COMPARISON),
    ("勞基法第38條", IntentType.EXACT),
    ("民法 184", IntentType.EXACT),
    ("公司法股東會", IntentType.SEMANTIC),
    ("加班費計算標準", IntentType.SEMANTIC),
])
def test_intent_classification_examples(query, expected_intent):
    result = classifier.classify(query)
    assert result.intent == expected_intent, f"Query: {query!r}, expected {expected_intent}, got {result.intent}"


def test_exact_returns_law_name_and_article():
    result = classifier.classify("勞基法第38條")
    assert result.intent == IntentType.EXACT
    assert result.law_name == "勞基法"
    assert result.article_no is not None


def test_exact_no_law_name():
    result = classifier.classify("第38條規定")
    assert result.intent == IntentType.EXACT
    assert result.law_name is None


def test_priority_exact_over_comparison():
    """比較勞基法第38條 → exact（exact 優先於 comparison）"""
    result = classifier.classify("比較勞基法第38條")
    assert result.intent == IntentType.EXACT


def test_priority_exact_over_definition():
    result = classifier.classify("什麼是勞基法第38條")
    assert result.intent == IntentType.EXACT


def test_priority_exact_over_procedure():
    result = classifier.classify("如何適用勞基法第38條")
    assert result.intent == IntentType.EXACT


def test_priority_comparison_over_definition():
    result = classifier.classify("比較什麼是勞動契約")
    assert result.intent == IntentType.COMPARISON


def test_priority_comparison_over_procedure():
    result = classifier.classify("比較如何申請加班費")
    assert result.intent == IntentType.COMPARISON


def test_priority_definition_over_procedure():
    result = classifier.classify("什麼是如何申請加班費的程序")
    assert result.intent == IntentType.DEFINITION


def test_result_is_classification_result():
    result = classifier.classify("加班費怎麼算")
    assert isinstance(result, ClassificationResult)


def test_semantic_has_no_law_name_or_article():
    result = classifier.classify("公司法股東會")
    assert result.intent == IntentType.SEMANTIC
    assert result.law_name is None
    assert result.article_no is None


def test_empty_query_returns_semantic():
    result = classifier.classify("")
    assert result.intent == IntentType.SEMANTIC


def test_whitespace_query():
    result = classifier.classify("   ")
    assert result.intent == IntentType.SEMANTIC
