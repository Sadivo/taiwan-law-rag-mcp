"""
api/session_routes.py
Session API 端點：POST /session, POST /session/{id}/chat, DELETE /session/{id}
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from api.models import (
    CreateSessionResponse,
    DeleteSessionResponse,
    SessionChatRequest,
    SessionChatResponse,
)
from generation.base import GenerationProviderError
from retrieval.context_manager import ContextManager, ConversationTurn

logger = logging.getLogger(__name__)

router = APIRouter()

# Shared ContextManager singleton
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


def _get_rag_chain():
    """Thin wrapper so tests can patch this easily."""
    from api.chat_routes import get_rag_chain
    return get_rag_chain()


@router.post("/session", response_model=CreateSessionResponse)
async def create_session(cm: ContextManager = Depends(get_context_manager)):
    """建立新 Session，回傳 session_id"""
    session_id = cm.create_session()
    return CreateSessionResponse(session_id=session_id)


@router.post("/session/{session_id}/chat", response_model=SessionChatResponse)
async def session_chat(
    session_id: str,
    request: SessionChatRequest,
    cm: ContextManager = Depends(get_context_manager),
):
    """在指定 Session 中進行對話"""
    rag_chain = _get_rag_chain()
    try:
        start = time.time()
        response = rag_chain.ask(request.question, request.top_k, session_id=session_id)
        query_time = time.time() - start

        # 儲存本輪對話
        turn = ConversationTurn(
            query=request.question,
            response=response.answer[:500],  # 儲存摘要
        )
        cm.add_turn(session_id, turn)

        return SessionChatResponse(
            answer=response.answer,
            citations=response.citations,
            query_time=response.query_time,
            session_id=session_id,
        )
    except GenerationProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("session_chat error: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail=f"Service error: {exc}")


@router.delete("/session/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(
    session_id: str,
    cm: ContextManager = Depends(get_context_manager),
):
    """刪除指定 Session"""
    deleted = cm.delete_session(session_id)
    return DeleteSessionResponse(deleted=deleted, session_id=session_id)
