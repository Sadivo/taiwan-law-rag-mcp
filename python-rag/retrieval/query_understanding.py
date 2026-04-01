"""
retrieval/query_understanding.py
QueryUnderstanding — 整合入口
"""
from __future__ import annotations

import logging
from typing import Optional

from retrieval.query_classifier import QueryClassifier, IntentType
from retrieval.query_rewriter import LanguageDetector, QueryRewriter, RewrittenQuery
from retrieval.context_manager import ContextManager

logger = logging.getLogger(__name__)


class QueryUnderstanding:
    """
    統一查詢理解入口。
    依序執行：語言偵測 → 翻譯 → 意圖分類 → 查詢改寫 → 上下文擴展
    任何子模組例外均捕捉，fallback 回傳以原始查詢為基礎的 RewrittenQuery。
    """

    def __init__(
        self,
        classifier: QueryClassifier,
        rewriter: QueryRewriter,
        context_manager: ContextManager,
        language_detector: LanguageDetector,
    ):
        self._classifier = classifier
        self._rewriter = rewriter
        self._context_manager = context_manager
        self._language_detector = language_detector

    def process(self, query: str, session_id: Optional[str] = None) -> RewrittenQuery:
        """
        處理查詢，回傳 RewrittenQuery。
        expanded_query 為最終送入 RetrievalService 的查詢字串，保證非空。
        """
        original = query

        try:
            # 1. 語言偵測
            language = self._language_detector.detect(query)

            # 2. 翻譯（英文 → 繁體中文）
            was_translated = False
            working_query = query
            if language == 'en':
                translated = self._rewriter.translate(query)
                if translated:
                    working_query = translated
                    was_translated = True

            # 3. 意圖分類
            classification = self._classifier.classify(working_query)
            intent = classification.intent

            # 4. 查詢改寫
            was_rewritten = False
            rewritten = self._rewriter.rewrite(working_query, intent)
            if rewritten != working_query:
                was_rewritten = True

            # 5. 上下文擴展
            expanded_query = rewritten
            if session_id is not None:
                expanded_query = self._context_manager.expand_with_context(rewritten, session_id)

            # 保證 expanded_query 非空
            if not expanded_query:
                expanded_query = original

            logger.debug(
                "QueryUnderstanding: intent=%s language=%s was_rewritten=%s",
                intent.value, language, was_rewritten,
            )

            return RewrittenQuery(
                original=original,
                rewritten=rewritten,
                expanded_query=expanded_query,
                intent=intent,
                language=language,
                was_translated=was_translated,
                was_rewritten=was_rewritten,
                law_name=classification.law_name,
                article_no=classification.article_no,
            )

        except Exception as exc:
            logger.warning("QueryUnderstanding.process() failed (%s), falling back to original query", exc)
            return RewrittenQuery(
                original=original,
                rewritten=original,
                expanded_query=original,
                intent=IntentType.SEMANTIC,
                language='zh',
                was_translated=False,
                was_rewritten=False,
                law_name=None,
                article_no=None,
            )
