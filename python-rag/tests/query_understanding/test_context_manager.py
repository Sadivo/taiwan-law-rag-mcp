"""
Tests for ContextManager — Properties 6, 7 (PBT) + unit tests
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from hypothesis import given, settings, strategies as st

from retrieval.context_manager import ContextManager, ConversationTurn, Session


def make_turn(query="test query", response="test response"):
    return ConversationTurn(query=query, response=response)


# ---------------------------------------------------------------------------
# Property 6: Session 對話輪次 Round-Trip
# ---------------------------------------------------------------------------

@given(
    query=st.text(min_size=1, max_size=100),
    response=st.text(min_size=1, max_size=100),
)
@settings(max_examples=100)
def test_property6_turn_roundtrip(query, response):
    """Property 6: add_turn 後立即查詢，能取回相同的 query 與 response"""
    cm = ContextManager()
    sid = cm.create_session()
    turn = ConversationTurn(query=query, response=response)
    cm.add_turn(sid, turn)
    session = cm.get_session(sid)
    assert session is not None
    assert len(session.turns) == 1
    retrieved = session.turns[-1]
    assert retrieved.query == query
    assert retrieved.response == response


# ---------------------------------------------------------------------------
# Property 7: Session 最多保留 10 輪
# ---------------------------------------------------------------------------

@given(n=st.integers(min_value=11, max_value=25))
@settings(max_examples=100)
def test_property7_max_10_turns(n):
    """Property 7: 新增超過 10 筆後，session 只保留最新 10 筆"""
    cm = ContextManager()
    sid = cm.create_session()
    for i in range(n):
        cm.add_turn(sid, ConversationTurn(query=f"q{i}", response=f"r{i}"))
    session = cm.get_session(sid)
    assert len(session.turns) == 10
    # 最新 10 筆：從 n-10 到 n-1
    turns_list = list(session.turns)
    assert turns_list[-1].query == f"q{n-1}"
    assert turns_list[0].query == f"q{n-10}"


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_create_session_returns_uuid():
    cm = ContextManager()
    sid = cm.create_session()
    import uuid
    uuid.UUID(sid, version=4)  # raises if invalid


def test_get_nonexistent_session_returns_none():
    cm = ContextManager()
    assert cm.get_session("nonexistent-id") is None


def test_add_turn_auto_creates_session():
    cm = ContextManager()
    cm.add_turn("new-session-id", make_turn())
    session = cm.get_session("new-session-id")
    assert session is not None
    assert len(session.turns) == 1


def test_delete_existing_session():
    cm = ContextManager()
    sid = cm.create_session()
    assert cm.delete_session(sid) is True
    assert cm.get_session(sid) is None


def test_delete_nonexistent_session_returns_false():
    cm = ContextManager()
    assert cm.delete_session("does-not-exist") is False


def test_expand_with_pronoun():
    cm = ContextManager()
    sid = cm.create_session()
    cm.add_turn(sid, ConversationTurn(query="勞基法加班費", response="..."))
    expanded = cm.expand_with_context("那第二條呢", sid)
    assert "勞基法加班費" in expanded
    assert "那第二條呢" in expanded


def test_expand_without_pronoun():
    cm = ContextManager()
    sid = cm.create_session()
    cm.add_turn(sid, ConversationTurn(query="勞基法加班費", response="..."))
    result = cm.expand_with_context("加班費計算方式", sid)
    assert result == "加班費計算方式"


def test_expand_no_history():
    cm = ContextManager()
    sid = cm.create_session()
    result = cm.expand_with_context("那第二條呢", sid)
    # No history → return original even with pronoun
    assert result == "那第二條呢"


def test_expand_nonexistent_session_auto_creates():
    cm = ContextManager()
    result = cm.expand_with_context("加班費", "ghost-session")
    assert result == "加班費"


def test_session_expiry_cleanup():
    """過期 Session 在下次存取時被清除"""
    cm = ContextManager()
    sid = cm.create_session()
    # Manually set last_active to past
    cm._sessions[sid].last_active = datetime.utcnow() - timedelta(seconds=1801)
    # Trigger cleanup via get_session
    result = cm.get_session(sid)
    assert result is None
    assert sid not in cm._sessions


def test_pronoun_detection_variants():
    cm = ContextManager()
    sid = cm.create_session()
    cm.add_turn(sid, ConversationTurn(query="勞基法", response="..."))
    for pronoun_query in ["這條怎麼說", "它的規定", "該法律", "還有其他規定嗎"]:
        result = cm.expand_with_context(pronoun_query, sid)
        assert "勞基法" in result, f"Expected expansion for {pronoun_query!r}"
