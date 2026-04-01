"""
api/chat_routes.py
Chat API 端點：POST /chat 與 POST /chat/stream
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.models import ChatRequest, ChatResponse
from generation.base import GenerationProviderError
from generation.rag_chain import RAGChain

logger = logging.getLogger(__name__)

router = APIRouter()
_rag_chain: Optional[RAGChain] = None


def get_rag_chain() -> RAGChain:
    """Singleton：初始化並回傳 RAGChain 實例"""
    global _rag_chain
    if _rag_chain is None:
        from retrieval.retrieval_service import RetrievalService
        from retrieval.hybrid_retriever import HybridRetriever
        from retrieval.vector_retriever import VectorRetriever
        from retrieval.bm25_retriever import BM25Retriever
        from providers.factory import ProviderFactory

        embedding_provider, reranking_provider = ProviderFactory.from_env()
        generation_provider = ProviderFactory.generation_from_env()

        top_k = int(os.environ.get("GENERATION_TOP_K", "5"))
        max_tokens = int(os.environ.get("GENERATION_MAX_TOKENS", "1024"))

        # Load data paths from env or defaults
        faiss_path = os.environ.get("FAISS_INDEX_PATH", "data/taiwan_law.faiss")
        chunks_path = os.environ.get("CHUNKS_PATH", "data/chunks.pkl")
        bm25_path = os.environ.get("BM25_INDEX_PATH", "data/bm25_index")

        vector_retriever = VectorRetriever(index_path=faiss_path, meta_path=chunks_path)
        bm25_retriever = BM25Retriever(index_dir=bm25_path)
        hybrid_retriever = HybridRetriever(
            vector_retriever=vector_retriever,
            bm25_retriever=bm25_retriever,
        )

        retrieval_service = RetrievalService(
            embedding_provider=embedding_provider,
            reranking_provider=reranking_provider,
            hybrid_retriever=hybrid_retriever,
        )

        _rag_chain = RAGChain(
            retrieval_service=retrieval_service,
            generation_provider=generation_provider,
            top_k=top_k,
            max_tokens=max_tokens,
        )

        # 依環境變數決定是否啟用 QueryUnderstanding
        enable_qu = os.environ.get("ENABLE_QUERY_REWRITING", "false").lower() == "true"
        if enable_qu:
            try:
                from retrieval.query_classifier import QueryClassifier
                from retrieval.query_rewriter import LanguageDetector, QueryRewriter
                from retrieval.context_manager import ContextManager
                from retrieval.query_understanding import QueryUnderstanding

                qu = QueryUnderstanding(
                    classifier=QueryClassifier(),
                    rewriter=QueryRewriter(generation_provider=generation_provider),
                    context_manager=ContextManager(),
                    language_detector=LanguageDetector(),
                )
                _rag_chain._query_understanding = qu
                logger.info("QueryUnderstanding enabled (ENABLE_QUERY_REWRITING=true)")
            except Exception as exc:
                logger.warning("Failed to initialize QueryUnderstanding: %s", exc)

    return _rag_chain


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, rag_chain: RAGChain = Depends(get_rag_chain)):
    """POST /chat — 回傳完整的 ChatResponse"""
    try:
        return rag_chain.ask(request.question, request.top_k)
    except GenerationProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("chat error: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail=f"Generation service error: {exc}")


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, rag_chain: RAGChain = Depends(get_rag_chain)):
    """POST /chat/stream — SSE 串流回應"""

    def generate():
        try:
            for token in rag_chain.ask_stream(request.question, request.top_k):
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.error("chat_stream error: %s", exc, exc_info=True)
            yield f"data: [ERROR] {exc}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
