"""Unit tests for MetricsCalculator."""

import math
import pytest
from evaluation.metrics import MetricsCalculator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_doc(law_name: str, article_no: str) -> dict:
    return {"law_name": law_name, "article_no": article_no}


LAW = "勞動基準法"
ART24 = "第 24 條"
ART25 = "第 25 條"
ART26 = "第 26 條"
ART27 = "第 27 條"
ART28 = "第 28 條"

KEY24 = f"{LAW}:{ART24}"
KEY25 = f"{LAW}:{ART25}"
KEY26 = f"{LAW}:{ART26}"


# ---------------------------------------------------------------------------
# match_key
# ---------------------------------------------------------------------------

def test_match_key_format():
    doc = make_doc(LAW, ART24)
    assert MetricsCalculator.match_key(doc) == KEY24


# ---------------------------------------------------------------------------
# recall_at_k
# ---------------------------------------------------------------------------

def test_recall_at_k_hit_at_position_3_k5():
    """5 docs, hit at position 3 (0-indexed 2), k=5 → 1 hit / 5 = 0.2"""
    results = [
        make_doc(LAW, ART25),
        make_doc(LAW, ART26),
        make_doc(LAW, ART24),  # hit
        make_doc(LAW, ART27),
        make_doc(LAW, ART28),
    ]
    expected = [KEY24]
    assert MetricsCalculator.recall_at_k(results, expected, k=5) == pytest.approx(1 / 5)


def test_recall_at_k_hit_at_position_3_k2():
    """Hit is at position 3 but k=2 → top-2 has no hit → 0.0"""
    results = [
        make_doc(LAW, ART25),
        make_doc(LAW, ART26),
        make_doc(LAW, ART24),  # hit, but beyond k=2
        make_doc(LAW, ART27),
        make_doc(LAW, ART28),
    ]
    expected = [KEY24]
    assert MetricsCalculator.recall_at_k(results, expected, k=2) == pytest.approx(0.0)


def test_recall_at_k_multiple_hits():
    """3 hits in top 5 → 3/5"""
    results = [
        make_doc(LAW, ART24),  # hit
        make_doc(LAW, ART25),  # hit
        make_doc(LAW, ART26),  # hit
        make_doc(LAW, ART27),
        make_doc(LAW, ART28),
    ]
    expected = [KEY24, KEY25, KEY26]
    assert MetricsCalculator.recall_at_k(results, expected, k=5) == pytest.approx(3 / 5)


def test_recall_at_k_empty_results():
    assert MetricsCalculator.recall_at_k([], [KEY24], k=5) == pytest.approx(0.0)


def test_recall_at_k_k_greater_than_results():
    """k > len(results) should not raise; uses actual length"""
    results = [make_doc(LAW, ART24)]
    expected = [KEY24]
    # effective_k = 1, 1 hit → 1/1 = 1.0
    assert MetricsCalculator.recall_at_k(results, expected, k=100) == pytest.approx(1.0)


def test_recall_at_k_no_hit():
    results = [make_doc(LAW, ART25), make_doc(LAW, ART26)]
    expected = [KEY24]
    assert MetricsCalculator.recall_at_k(results, expected, k=5) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# mrr
# ---------------------------------------------------------------------------

def test_mrr_first_hit_at_rank_2():
    """Single query, first hit at rank 2 → MRR = 0.5"""
    results = [make_doc(LAW, ART25), make_doc(LAW, ART24)]
    mrr = MetricsCalculator.mrr([results], [[KEY24]])
    assert mrr == pytest.approx(0.5)


def test_mrr_first_hit_at_rank_1():
    results = [make_doc(LAW, ART24), make_doc(LAW, ART25)]
    mrr = MetricsCalculator.mrr([results], [[KEY24]])
    assert mrr == pytest.approx(1.0)


def test_mrr_no_hit():
    results = [make_doc(LAW, ART25), make_doc(LAW, ART26)]
    mrr = MetricsCalculator.mrr([results], [[KEY24]])
    assert mrr == pytest.approx(0.0)


def test_mrr_multiple_queries():
    """Two queries: rank-1 hit (RR=1.0) and rank-2 hit (RR=0.5) → MRR=0.75"""
    q1 = [make_doc(LAW, ART24)]
    q2 = [make_doc(LAW, ART25), make_doc(LAW, ART24)]
    mrr = MetricsCalculator.mrr([q1, q2], [[KEY24], [KEY24]])
    assert mrr == pytest.approx(0.75)


def test_mrr_empty_results_list():
    assert MetricsCalculator.mrr([], []) == pytest.approx(0.0)


def test_mrr_empty_inner_results():
    """Query with empty results contributes RR=0"""
    mrr = MetricsCalculator.mrr([[]], [[KEY24]])
    assert mrr == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# ndcg_at_k
# ---------------------------------------------------------------------------

def test_ndcg_at_k_perfect_ranking():
    """Single relevant doc at rank 1 → DCG = IDCG = 1/log2(2) = 1.0 → NDCG = 1.0"""
    results = [make_doc(LAW, ART24)]
    assert MetricsCalculator.ndcg_at_k(results, [KEY24], k=1) == pytest.approx(1.0)


def test_ndcg_at_k_hit_at_rank_2():
    """Relevant doc at rank 2, k=2, 1 expected.
    DCG  = 1/log2(3)
    IDCG = 1/log2(2) = 1.0
    NDCG = (1/log2(3)) / 1.0
    """
    results = [make_doc(LAW, ART25), make_doc(LAW, ART24)]
    expected = [KEY24]
    expected_ndcg = (1.0 / math.log2(3)) / (1.0 / math.log2(2))
    assert MetricsCalculator.ndcg_at_k(results, expected, k=2) == pytest.approx(expected_ndcg)


def test_ndcg_at_k_no_hit():
    results = [make_doc(LAW, ART25), make_doc(LAW, ART26)]
    assert MetricsCalculator.ndcg_at_k(results, [KEY24], k=5) == pytest.approx(0.0)


def test_ndcg_at_k_empty_results():
    assert MetricsCalculator.ndcg_at_k([], [KEY24], k=5) == pytest.approx(0.0)


def test_ndcg_at_k_k_greater_than_results():
    """k > len(results) should not raise"""
    results = [make_doc(LAW, ART24)]
    # effective_k=1, hit at rank 1 → NDCG=1.0
    assert MetricsCalculator.ndcg_at_k(results, [KEY24], k=100) == pytest.approx(1.0)


def test_ndcg_at_k_multiple_relevant():
    """2 relevant docs at ranks 1 and 2, k=2.
    DCG  = 1/log2(2) + 1/log2(3)
    IDCG = 1/log2(2) + 1/log2(3)  (ideal = same)
    NDCG = 1.0
    """
    results = [make_doc(LAW, ART24), make_doc(LAW, ART25)]
    expected = [KEY24, KEY25]
    assert MetricsCalculator.ndcg_at_k(results, expected, k=2) == pytest.approx(1.0)
