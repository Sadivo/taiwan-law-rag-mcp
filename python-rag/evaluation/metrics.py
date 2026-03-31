"""Metrics calculator for the evaluation pipeline."""

import math
from typing import Dict, List


class MetricsCalculator:
    """Pure stateless metrics calculator for IR evaluation."""

    @staticmethod
    def match_key(doc: Dict) -> str:
        """產生 '{law_name}:{article_no}' 匹配鍵"""
        return f"{doc['law_name']}:{doc['article_no']}"

    @staticmethod
    def recall_at_k(results: List[Dict], expected: List[str], k: int) -> float:
        """Recall@K：前 min(k, len(results)) 筆中命中 expected 的比例。

        回傳命中數 / effective_k；若 effective_k == 0 回傳 0.0。
        """
        effective_k = min(k, len(results))
        if effective_k == 0:
            return 0.0
        expected_set = set(expected)
        hits = sum(
            1
            for doc in results[:effective_k]
            if MetricsCalculator.match_key(doc) in expected_set
        )
        return hits / effective_k

    @staticmethod
    def mrr(results_list: List[List[Dict]], expected_list: List[List[str]]) -> float:
        """MRR：多個查詢的平均倒數排名。

        對每個查詢找第一個命中的排名（1-indexed），取倒數後平均。
        若查詢列表為空回傳 0.0。
        """
        if not results_list:
            return 0.0
        total = 0.0
        for results, expected in zip(results_list, expected_list):
            expected_set = set(expected)
            for rank, doc in enumerate(results, start=1):
                if MetricsCalculator.match_key(doc) in expected_set:
                    total += 1.0 / rank
                    break
        return total / len(results_list)

    @staticmethod
    def ndcg_at_k(results: List[Dict], expected: List[str], k: int) -> float:
        """NDCG@K：考慮排名折扣的正規化累積增益（二元相關性）。

        DCG@K  = Σ rel_i / log2(i+1)  for i in 1..effective_k
        IDCG@K = Σ 1/log2(i+1)        for i in 1..min(effective_k, |expected|)
        NDCG@K = DCG@K / IDCG@K  (若 IDCG == 0 回傳 0.0)
        """
        effective_k = min(k, len(results))
        if effective_k == 0:
            return 0.0
        expected_set = set(expected)

        dcg = sum(
            (1.0 / math.log2(i + 1))
            for i, doc in enumerate(results[:effective_k], start=1)
            if MetricsCalculator.match_key(doc) in expected_set
        )

        ideal_hits = min(effective_k, len(expected))
        idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))

        if idcg == 0.0:
            return 0.0
        return dcg / idcg
