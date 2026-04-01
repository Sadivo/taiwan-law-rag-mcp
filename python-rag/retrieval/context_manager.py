"""
retrieval/context_manager.py
ConversationTurn, Session, ContextManager
"""
from __future__ import annotations

import logging
import re
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

TTL_SECONDS = 1800  # 30 minutes

# 指代詞模式
_PRONOUN_PATTERN = re.compile(r'那|這|它|該|第[二三四五六七八九十]+條|還有|其他')


@dataclass
class ConversationTurn:
    query: str
    response: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Session:
    session_id: str
    turns: deque = field(default_factory=lambda: deque(maxlen=10))
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)


class ContextManager:
    """
    多輪對話上下文管理器。
    - TTL = 1800 秒（30 分鐘），惰性清除
    - 每個 Session 最多保留 10 輪
    - 指代詞偵測後擴展查詢
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create_session(self) -> str:
        """建立新 Session，回傳 session_id（UUID v4）"""
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = Session(session_id=session_id)
        logger.debug("Created session %s", session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[Session]:
        """取得 Session；若不存在或已過期回傳 None"""
        self._cleanup_expired()
        return self._sessions.get(session_id)

    def _get_or_create(self, session_id: str) -> Session:
        """取得 Session；若不存在則自動建立"""
        self._cleanup_expired()
        if session_id not in self._sessions:
            logger.debug("Session %s not found, creating new one", session_id)
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    def add_turn(self, session_id: str, turn: ConversationTurn) -> None:
        """新增對話輪次；session 不存在時自動建立"""
        session = self._get_or_create(session_id)
        session.turns.append(turn)
        session.last_active = datetime.utcnow()

    def expand_with_context(self, query: str, session_id: str) -> str:
        """
        若查詢含指代詞，結合最近一輪的 query 擴展為 '{last_query} {current_query}'。
        session 不存在時直接回傳原始查詢。
        """
        session = self._get_or_create(session_id)
        if session.turns and _PRONOUN_PATTERN.search(query):
            last_turn = session.turns[-1]
            expanded = f"{last_turn.query} {query}"
            logger.debug("Expanded query: %r -> %r", query, expanded)
            return expanded
        return query

    def delete_session(self, session_id: str) -> bool:
        """刪除 Session，回傳是否存在"""
        existed = session_id in self._sessions
        self._sessions.pop(session_id, None)
        return existed

    def _cleanup_expired(self) -> None:
        """惰性清除過期 Session"""
        now = datetime.utcnow()
        expired = [
            sid for sid, s in self._sessions.items()
            if (now - s.last_active).total_seconds() > TTL_SECONDS
        ]
        for sid in expired:
            logger.debug("Removing expired session %s", sid)
            del self._sessions[sid]
