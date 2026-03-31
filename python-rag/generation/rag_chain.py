"""
generation/rag_chain.py
RAGChain — 整合 retrieval 與 generation 的完整問答流程
"""
from __future__ import annotations

import time
import logging
from typing import Any, Dict, Iterator, List, Optional

from api.models import ChatResponse, Citation
from generation.base import GenerationProvider

logger = logging.getLogger(__name__)

_EMPTY_RESULT_ANSWER = "根據現有資料庫，找不到與您問題相關的法律條文，建議諮詢專業律師。"

_SYSTEM_PROMPT_TEMPLATE = """你是一位台灣法律助理，請根據以下法律條文回答問題。
回答時必須引用具體條文，不得捏造法律內容。

相關法律條文：
{retrieved_articles}

問題：{user_question}

請用繁體中文回答，並在回答末尾列出引用的條文來源。"""


class RAGChain:
    def __init__(
        self,
        retrieval_service,
        generation_provider: GenerationProvider,
        top_k: int = 5,
        max_tokens: int = 1024,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._generation_provider = generation_provider
        self._top_k = top_k
        self._max_tokens = max_tokens

    def _build_context(self, articles: List[Dict[str, Any]]) -> str:
        """格式化條文為 context 字串：【{law_name} {article_no}】{content}"""
        parts = []
        for article in articles:
            law_name = article.get("law_name", "")
            article_no = article.get("article_no", "")
            content = article.get("content", "")
            parts.append(f"【{law_name} {article_no}】{content}")
        return "\n".join(parts)

    def _build_prompt(self, context: str, question: str) -> str:
        """依 system prompt 結構建構完整 prompt"""
        return _SYSTEM_PROMPT_TEMPLATE.format(
            retrieved_articles=context,
            user_question=question,
        )

    def _extract_citations(self, articles: List[Dict[str, Any]]) -> List[Citation]:
        """從 retrieval 結果提取引用條文"""
        return [
            Citation(
                law_name=article.get("law_name", ""),
                article_no=article.get("article_no", ""),
            )
            for article in articles
        ]

    def ask(self, question: str, top_k: Optional[int] = None) -> ChatResponse:
        """執行完整 RAG 問答流程，回傳 ChatResponse"""
        start_time = time.time()
        effective_top_k = top_k if top_k is not None else self._top_k

        articles = self._retrieval_service.search_semantic(question, effective_top_k)

        if not articles:
            return ChatResponse(
                answer=_EMPTY_RESULT_ANSWER,
                citations=[],
                query_time=time.time() - start_time,
            )

        context = self._build_context(articles)
        prompt = self._build_prompt(context, question)
        answer = self._generation_provider.generate(prompt)
        citations = self._extract_citations(articles)

        return ChatResponse(
            answer=answer,
            citations=citations,
            query_time=time.time() - start_time,
        )

    def ask_stream(self, question: str, top_k: Optional[int] = None) -> Iterator[str]:
        """執行 RAG 問答流程，以串流方式逐 token 回傳生成內容"""
        effective_top_k = top_k if top_k is not None else self._top_k

        articles = self._retrieval_service.search_semantic(question, effective_top_k)

        if not articles:
            yield _EMPTY_RESULT_ANSWER
            return

        context = self._build_context(articles)
        prompt = self._build_prompt(context, question)

        for token in self._generation_provider.generate_stream(prompt):
            yield token
