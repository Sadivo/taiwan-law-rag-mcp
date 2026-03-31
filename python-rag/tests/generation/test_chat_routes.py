"""
tests/generation/test_chat_routes.py
Properties 11–12 for Chat API endpoints
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import MagicMock

import httpx
from fastapi import FastAPI
from hypothesis import given, settings
from hypothesis import strategies as st

from api.chat_routes import router, get_rag_chain
from api.models import ChatResponse, Citation

# ---------------------------------------------------------------------------
# Test app setup
# ---------------------------------------------------------------------------

app = FastAPI()
app.include_router(router)


def _make_mock_rag_chain(answer="mock answer", citations=None, query_time=0.1, tokens=None):
    mock = MagicMock()
    mock.ask.return_value = ChatResponse(
        answer=answer,
        citations=citations or [Citation(law_name="勞動基準法", article_no="第 38 條")],
        query_time=query_time,
    )
    mock.ask_stream.return_value = iter(tokens or ["token1", "token2"])
    return mock


async def _async_post(path: str, payload: dict) -> httpx.Response:
    """Send a POST request to the test app using AsyncClient + ASGITransport."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.post(path, json=payload)


def _sync_post(path: str, payload: dict) -> httpx.Response:
    return asyncio.get_event_loop().run_until_complete(_async_post(path, payload))


# ---------------------------------------------------------------------------
# Property 11: POST /chat 回傳完整 ChatResponse
# Validates: Requirements 7.1, 7.2
# ---------------------------------------------------------------------------

@given(st.text(min_size=1))
@settings(max_examples=100)
def test_post_chat_returns_complete_response(question: str):
    """
    Feature: rag-generation, Property 11: POST /chat 回傳完整 ChatResponse
    Validates: Requirements 7.1, 7.2

    對任意有效 ChatRequest（非空問題），POST /chat 應回傳 HTTP 200
    且 JSON body 包含 answer、citations、query_time。
    """
    mock_chain = _make_mock_rag_chain()
    app.dependency_overrides[get_rag_chain] = lambda: mock_chain
    try:
        response = _sync_post("/chat", {"question": question, "top_k": 5})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert "citations" in body
    assert "query_time" in body
    assert isinstance(body["answer"], str)
    assert isinstance(body["citations"], list)
    assert isinstance(body["query_time"], (int, float))


# ---------------------------------------------------------------------------
# Property 12: SSE 格式符合規範
# Validates: Requirements 8.2, 8.3
# ---------------------------------------------------------------------------

@given(st.lists(st.text(), min_size=1))
@settings(max_examples=100)
def test_sse_format_matches_spec(tokens: list):
    """
    Feature: rag-generation, Property 12: SSE 格式符合規範
    Validates: Requirements 8.2, 8.3

    對任意 token 序列，SSE 回應應將每個 token 格式化為 data: {token}\\n\\n，
    並以 data: [DONE]\\n\\n 結尾。
    """
    mock_chain = _make_mock_rag_chain(tokens=tokens)
    app.dependency_overrides[get_rag_chain] = lambda: mock_chain
    try:
        response = _sync_post("/chat/stream", {"question": "test question", "top_k": 5})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    content = response.text

    # Each token should be formatted as "data: {token}\n\n"
    for token in tokens:
        assert f"data: {token}\n\n" in content

    # Must end with [DONE]
    assert content.endswith("data: [DONE]\n\n")
