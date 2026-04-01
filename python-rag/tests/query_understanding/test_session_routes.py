"""
Tests for Session API endpoints
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import asyncio
import uuid
import pytest
from unittest.mock import MagicMock, patch

import httpx
from fastapi import FastAPI

from api.models import ChatResponse, Citation
from api.session_routes import router as session_router, get_context_manager
from retrieval.context_manager import ContextManager


def make_mock_rag_chain(answer="測試回答"):
    chain = MagicMock()
    chain.ask.return_value = ChatResponse(
        answer=answer,
        citations=[Citation(law_name="勞動基準法", article_no="第 38 條")],
        query_time=0.1,
    )
    return chain


def make_test_app(cm: ContextManager) -> FastAPI:
    app = FastAPI()
    app.include_router(session_router)
    app.dependency_overrides[get_context_manager] = lambda: cm
    return app


async def _request(app, method: str, path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await getattr(client, method)(path, **kwargs)


def req(app, method, path, **kwargs):
    return asyncio.get_event_loop().run_until_complete(_request(app, method, path, **kwargs))


@pytest.fixture
def setup():
    cm = ContextManager()
    mock_chain = make_mock_rag_chain()
    with patch("api.session_routes._get_rag_chain", return_value=mock_chain):
        app = make_test_app(cm)
        yield app, cm


# ---------------------------------------------------------------------------
# POST /session
# ---------------------------------------------------------------------------

def test_create_session_returns_valid_uuid(setup):
    app, _ = setup
    resp = req(app, "post", "/session")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    uuid.UUID(data["session_id"], version=4)


def test_create_session_unique_ids(setup):
    app, _ = setup
    ids = {req(app, "post", "/session").json()["session_id"] for _ in range(5)}
    assert len(ids) == 5


# ---------------------------------------------------------------------------
# POST /session/{id}/chat
# ---------------------------------------------------------------------------

def test_session_chat_normal_flow(setup):
    app, _ = setup
    sid = req(app, "post", "/session").json()["session_id"]
    resp = req(app, "post", f"/session/{sid}/chat", json={"question": "加班費怎麼算", "top_k": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == sid
    assert "answer" in data
    assert "citations" in data
    assert "query_time" in data


def test_session_chat_auto_creates_session(setup):
    app, _ = setup
    fake_sid = str(uuid.uuid4())
    resp = req(app, "post", f"/session/{fake_sid}/chat", json={"question": "加班費怎麼算"})
    assert resp.status_code == 200
    assert resp.json()["session_id"] == fake_sid


def test_session_chat_stores_turn(setup):
    app, cm = setup
    sid = req(app, "post", "/session").json()["session_id"]
    req(app, "post", f"/session/{sid}/chat", json={"question": "加班費怎麼算"})
    session = cm.get_session(sid)
    assert session is not None
    assert len(session.turns) == 1
    assert session.turns[0].query == "加班費怎麼算"


def test_session_chat_empty_question_returns_422(setup):
    app, _ = setup
    sid = req(app, "post", "/session").json()["session_id"]
    resp = req(app, "post", f"/session/{sid}/chat", json={"question": ""})
    assert resp.status_code == 422


def test_session_chat_missing_question_returns_422(setup):
    app, _ = setup
    sid = req(app, "post", "/session").json()["session_id"]
    resp = req(app, "post", f"/session/{sid}/chat", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /session/{id}
# ---------------------------------------------------------------------------

def test_delete_existing_session(setup):
    app, _ = setup
    sid = req(app, "post", "/session").json()["session_id"]
    resp = req(app, "delete", f"/session/{sid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] is True
    assert data["session_id"] == sid


def test_delete_nonexistent_session(setup):
    app, _ = setup
    fake_sid = str(uuid.uuid4())
    resp = req(app, "delete", f"/session/{fake_sid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] is False
    assert data["session_id"] == fake_sid
