"""
retrieval/query_rewriter.py
LanguageDetector + QueryRewriter
"""
from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LanguageDetector
# ---------------------------------------------------------------------------

class LanguageDetector:
    """
    純規則語言偵測器。
    CJK 字元比例 > 0.3 → 'zh'
    ASCII 字母比例 > 0.5 → 'en'
    其他 → 'zh'（預設）
    """

    @staticmethod
    def _is_cjk(ch: str) -> bool:
        cp = ord(ch)
        return (
            0x4E00 <= cp <= 0x9FFF   # CJK Unified Ideographs
            or 0x3400 <= cp <= 0x4DBF  # CJK Extension A
            or 0x20000 <= cp <= 0x2A6DF  # CJK Extension B
            or 0xF900 <= cp <= 0xFAFF  # CJK Compatibility Ideographs
            or 0x2E80 <= cp <= 0x2EFF  # CJK Radicals Supplement
            or 0x3000 <= cp <= 0x303F  # CJK Symbols and Punctuation
        )

    def detect(self, text: str) -> str:
        """回傳 'zh' 或 'en'"""
        if not text:
            return 'zh'

        total = len(text)
        cjk_count = sum(1 for ch in text if self._is_cjk(ch))
        ascii_alpha_count = sum(1 for ch in text if ch.isascii() and ch.isalpha())

        cjk_ratio = cjk_count / total
        ascii_ratio = ascii_alpha_count / total

        if cjk_ratio > 0.3:
            return 'zh'
        if ascii_ratio > 0.5:
            return 'en'
        return 'zh'


# ---------------------------------------------------------------------------
# RewrittenQuery dataclass
# ---------------------------------------------------------------------------

@dataclass
class RewrittenQuery:
    original: str
    rewritten: str
    expanded_query: str
    intent: object  # IntentType — avoid circular import; caller sets this
    language: str
    was_translated: bool = False
    was_rewritten: bool = False
    law_name: Optional[str] = None
    article_no: Optional[str] = None


# ---------------------------------------------------------------------------
# QueryRewriter
# ---------------------------------------------------------------------------

_REWRITE_PROMPT_TEMPLATE = (
    "請將以下口語法律問題改寫為適合向量搜尋的法律關鍵字組合，"
    "只輸出改寫後的關鍵字，不要解釋：\n{query}"
)

_TRANSLATE_PROMPT_TEMPLATE = (
    "請將以下英文翻譯為繁體中文，只輸出翻譯結果，不要解釋：\n{query}"
)


class QueryRewriter:
    """
    查詢改寫器。
    - exact 意圖：直接回傳原始查詢
    - semantic/procedure：呼叫 LLM 改寫
    - LLM 不可用或超時：fallback 原始查詢
    - 查詢超過 max_length 字元時截斷後再改寫（original 保留完整）
    """

    def __init__(
        self,
        generation_provider=None,
        timeout: float = 10.0,
        max_length: int = 500,
    ):
        self._provider = generation_provider
        self._timeout = timeout
        self._max_length = max_length

    def rewrite(self, query: str, intent) -> str:
        """
        回傳改寫後的查詢字串。
        exact 意圖直接回傳原始查詢；其他意圖嘗試 LLM 改寫。
        """
        from retrieval.query_classifier import IntentType

        if intent == IntentType.EXACT:
            return query

        if self._provider is None:
            return query

        work_query = query[:self._max_length] if len(query) > self._max_length else query

        try:
            import signal

            # Windows 不支援 SIGALRM，改用 concurrent.futures timeout
            import concurrent.futures
            prompt = _REWRITE_PROMPT_TEMPLATE.format(query=work_query)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._provider.generate, prompt)
                try:
                    result = future.result(timeout=self._timeout)
                    return result.strip() if result else query
                except concurrent.futures.TimeoutError:
                    logger.warning("QueryRewriter: LLM rewrite timed out, using original query")
                    return query
        except Exception as exc:
            logger.warning("QueryRewriter: rewrite failed (%s), using original query", exc)
            return query

    def translate(self, query: str) -> Optional[str]:
        """
        英文 → 繁體中文翻譯。失敗時回傳 None。
        """
        if self._provider is None:
            return None

        try:
            import concurrent.futures
            prompt = _TRANSLATE_PROMPT_TEMPLATE.format(query=query)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._provider.generate, prompt)
                try:
                    result = future.result(timeout=self._timeout)
                    return result.strip() if result else None
                except concurrent.futures.TimeoutError:
                    logger.warning("QueryRewriter: translation timed out")
                    return None
        except Exception as exc:
            logger.warning("QueryRewriter: translation failed (%s)", exc)
            return None
