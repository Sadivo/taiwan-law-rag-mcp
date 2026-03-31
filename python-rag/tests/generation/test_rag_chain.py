"""
tests/generation/test_rag_chain.py
Properties 6–10 for RAGChain
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from api.models import ChatResponse, Citation
from generation.rag_chain import RAGChain, _EMPTY_RESULT_ANSWER


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_retrieval_service(articles):
    mock = MagicMock()
    mock.search_semantic.return_value = articles
    return mock


def _make_generation_provider(answer="mock answer", tokens=None):
    mock = MagicMock()
    mock.generate.return_value = answer
    mock.generate_stream.return_value = iter(tokens or ["tok1", "tok2"])
    return mock


_article_strategy = st.fixed_dictionaries({
    "law_name": st.text(),
    "article_no": st.text(),
    "content": st.text(),
})


# ---------------------------------------------------------------------------
# Property 6: ask() 回傳完整的 ChatResponse
# Validates: Requirements 4.1, 4.4
# ---------------------------------------------------------------------------

@given(st.text(min_size=1))
@settings(max_examples=100)
def test_ask_returns_complete_chat_response(question: str):
    """
    Feature: rag-generation, Property 6: ask() 回傳完整的 ChatResponse
    Validates: Requirements 4.1, 4.4

    對任意非空問題，ask() 應回傳含非空 answer、citations list、非負 query_time 的 ChatResponse。
    """
    articles = [{"law_name": "勞動基準法", "article_no": "第 38 條", "content": "內容"}]
    retrieval = _make_retrieval_service(articles)
    generation = _make_generation_provider(answer="這是回答")

    chain = RAGChain(retrieval, generation)
    result = chain.ask(question)

    assert isinstance(result, ChatResponse)
    assert len(result.answer) > 0
    assert isinstance(result.citations, list)
    assert result.query_time >= 0


# ---------------------------------------------------------------------------
# Property 7: context 格式符合規範
# Validates: Requirements 4.3
# ---------------------------------------------------------------------------

@given(st.lists(_article_strategy))
@settings(max_examples=100)
def test_context_format_matches_spec(articles):
    """
    Feature: rag-generation, Property 7: context 格式符合規範
    Validates: Requirements 4.3

    對任意條文列表，_build_context 應將每筆格式化為 【{law_name} {article_no}】{content}。
    """
    retrieval = _make_retrieval_service([])
    generation = _make_generation_provider()
    chain = RAGChain(retrieval, generation)

    context = chain._build_context(articles)

    for article in articles:
        expected = f"【{article['law_name']} {article['article_no']}】{article['content']}"
        assert expected in context


# ---------------------------------------------------------------------------
# Property 8: prompt 包含必要結構元素
# Validates: Requirements 4.2
# ---------------------------------------------------------------------------

@given(
    question=st.text(min_size=1),
    articles=st.lists(_article_strategy, min_size=1),
)
@settings(max_examples=100)
def test_prompt_contains_required_elements(question: str, articles):
    """
    Feature: rag-generation, Property 8: prompt 包含必要結構元素
    Validates: Requirements 4.2

    對任意問題與條文列表，prompt 應同時包含 context 與 user question。
    """
    retrieval = _make_retrieval_service([])
    generation = _make_generation_provider()
    chain = RAGChain(retrieval, generation)

    context = chain._build_context(articles)
    prompt = chain._build_prompt(context, question)

    assert context in prompt
    assert question in prompt


# ---------------------------------------------------------------------------
# Property 9: retrieval 為空時不呼叫 LLM
# Validates: Requirements 4.6
# ---------------------------------------------------------------------------

@given(st.text(min_size=1))
@settings(max_examples=100)
def test_empty_retrieval_does_not_call_llm(question: str):
    """
    Feature: rag-generation, Property 9: retrieval 為空時不呼叫 LLM
    Validates: Requirements 4.6

    當 retrieval 回傳空列表時，generate 不應被呼叫，且回傳固定回答。
    """
    retrieval = _make_retrieval_service([])
    generation = _make_generation_provider()

    chain = RAGChain(retrieval, generation)
    result = chain.ask(question)

    generation.generate.assert_not_called()
    assert result.answer == _EMPTY_RESULT_ANSWER
    assert result.citations == []


# ---------------------------------------------------------------------------
# Property 10: ask_stream() 回傳 retrieval 後的 token 串流
# Validates: Requirements 4.5
# ---------------------------------------------------------------------------

@given(st.text(min_size=1))
@settings(max_examples=100)
def test_ask_stream_yields_tokens_from_provider(question: str):
    """
    Feature: rag-generation, Property 10: ask_stream() 回傳 retrieval 後的 token 串流
    Validates: Requirements 4.5

    對任意非空問題，ask_stream() 應先執行 retrieval，再 yield generate_stream 的所有 token。
    """
    articles = [{"law_name": "民法", "article_no": "第 1 條", "content": "內容"}]
    expected_tokens = ["token_a", "token_b", "token_c"]

    retrieval = _make_retrieval_service(articles)
    generation = MagicMock()
    generation.generate_stream.return_value = iter(expected_tokens)

    chain = RAGChain(retrieval, generation)
    yielded = list(chain.ask_stream(question))

    retrieval.search_semantic.assert_called_once()
    assert yielded == expected_tokens
