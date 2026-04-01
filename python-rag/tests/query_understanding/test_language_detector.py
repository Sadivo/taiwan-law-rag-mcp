"""
Tests for LanguageDetector — Property 5 (PBT) + unit tests
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from hypothesis import given, settings, strategies as st

from retrieval.query_rewriter import LanguageDetector

detector = LanguageDetector()

# ---------------------------------------------------------------------------
# Property 5: 語言偵測一致性
# ---------------------------------------------------------------------------

# 純 CJK 字元（常用漢字範圍）
cjk_chars = st.text(
    alphabet=st.characters(min_codepoint=0x4E00, max_codepoint=0x9FFF),
    min_size=3,
)

# 純 ASCII 字母
ascii_chars = st.text(
    alphabet=st.characters(min_codepoint=ord('a'), max_codepoint=ord('z')),
    min_size=3,
)


@given(text=cjk_chars)
@settings(max_examples=100)
def test_property5_cjk_returns_zh(text):
    """Property 5: 純 CJK 字串 → 'zh'"""
    assert detector.detect(text) == 'zh', f"Expected 'zh' for CJK text: {text!r}"


@given(text=ascii_chars)
@settings(max_examples=100)
def test_property5_ascii_returns_en(text):
    """Property 5: 純 ASCII 字母字串 → 'en'"""
    assert detector.detect(text) == 'en', f"Expected 'en' for ASCII text: {text!r}"


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_pure_chinese():
    assert detector.detect("加班費如何計算") == 'zh'


def test_pure_english():
    assert detector.detect("how to calculate overtime pay") == 'en'


def test_mixed_mostly_chinese():
    # 中文為主，少量英文
    assert detector.detect("加班費 overtime 計算") == 'zh'


def test_mixed_mostly_english():
    # 英文為主，少量中文
    assert detector.detect("overtime pay 加班") == 'en'


def test_empty_string():
    assert detector.detect("") == 'zh'


def test_numbers_only():
    # 純數字，無 CJK 也無 ASCII 字母 → 預設 zh
    assert detector.detect("12345") == 'zh'


def test_symbols_only():
    assert detector.detect("!@#$%") == 'zh'


def test_single_cjk_char():
    assert detector.detect("法") == 'zh'


def test_single_ascii_char():
    # 單一字元，ASCII 比例 = 1.0 > 0.5 → en
    assert detector.detect("a") == 'en'


def test_mixed_boundary_cjk_dominant():
    # 4 CJK + 1 ASCII → CJK ratio = 0.8 > 0.3 → zh
    assert detector.detect("勞基法a") == 'zh'
