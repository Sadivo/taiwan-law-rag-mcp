"""Unit tests for evaluation/evaluator.py."""

from unittest.mock import MagicMock

import pytest

from evaluation.evaluator import (
    BM25OnlyStrategy,
    Evaluator,
    HybridStrategy,
    VectorOnlyStrategy,
)
from evaluation.models import EvalQuery


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doc(law_name: str, article_no: str) -> dict:
    return {"law_name": law_name, "article_no": article_no, "id": f"{law_name}:{article_no}"}


def _make_query(query: str = "test", law: str = "勞動基準法", articles=None, qt: str = "semantic") -> EvalQuery:
    return EvalQuery(
        query=query,
        expected_law=law,
        expected_articles=articles or ["第 24 條"],
        query_type=qt,
    )


def _make_evaluator(reranking_provider=None):
    embedding_provider = MagicMock()
    embedding_provider.embed_query.return_value = [0.1, 0.2, 0.3]

    vector_retriever = MagicMock()
    bm25_retriever = MagicMock()
    hybrid_retriever = MagicMock()

    return Evaluator(
        embedding_provider=embedding_provider,
        reranking_provider=reranking_provider,
        vector_retriever=vector_retriever,
        bm25_retriever=bm25_retriever,
        hybrid_retriever=hybrid_retriever,
    )


# ---------------------------------------------------------------------------
# build_strategies() tests
# ---------------------------------------------------------------------------


class TestBuildStrategies:
    def test_default_strategy_count_without_reranker(self):
        """Without reranking provider: 1 vector + 1 bm25 + 3 hybrid = 5."""
        ev = _make_evaluator(reranking_provider=None)
        strategies = ev.build_strategies(rrf_k_values=[10, 30, 60], test_reranker=True)
        assert len(strategies) == 5

    def test_default_strategy_count_with_reranker(self):
        """With reranking provider: 1 vector + 1 bm25 + 3 hybrid + 3 hybrid_reranked = 8."""
        reranking_provider = MagicMock()
        ev = _make_evaluator(reranking_provider=reranking_provider)
        strategies = ev.build_strategies(rrf_k_values=[10, 30, 60], test_reranker=True)
        assert len(strategies) == 8

    def test_test_reranker_false_skips_reranked_strategies(self):
        """test_reranker=False should not add reranked strategies even if provider exists."""
        reranking_provider = MagicMock()
        ev = _make_evaluator(reranking_provider=reranking_provider)
        strategies = ev.build_strategies(rrf_k_values=[10, 30, 60], test_reranker=False)
        assert len(strategies) == 5

    def test_strategy_names(self):
        """Strategy names should follow the expected naming convention."""
        ev = _make_evaluator(reranking_provider=None)
        strategies = ev.build_strategies(rrf_k_values=[10, 30], test_reranker=False)
        names = [s.name for s in strategies]
        assert "vector" in names
        assert "bm25" in names
        assert "hybrid_rrf10" in names
        assert "hybrid_rrf30" in names

    def test_reranked_strategy_names(self):
        """Reranked hybrid strategies should have '_reranked' suffix."""
        reranking_provider = MagicMock()
        ev = _make_evaluator(reranking_provider=reranking_provider)
        strategies = ev.build_strategies(rrf_k_values=[60], test_reranker=True)
        names = [s.name for s in strategies]
        assert "hybrid_rrf60_reranked" in names

    def test_custom_rrf_k_values(self):
        """Custom rrf_k_values should produce the right number of hybrid strategies."""
        ev = _make_evaluator(reranking_provider=None)
        strategies = ev.build_strategies(rrf_k_values=[5, 20], test_reranker=False)
        # 1 vector + 1 bm25 + 2 hybrid
        assert len(strategies) == 4

    def test_strategy_types(self):
        """Returned strategies should be instances of the correct classes."""
        ev = _make_evaluator(reranking_provider=None)
        strategies = ev.build_strategies(rrf_k_values=[10], test_reranker=False)
        assert any(isinstance(s, VectorOnlyStrategy) for s in strategies)
        assert any(isinstance(s, BM25OnlyStrategy) for s in strategies)
        assert any(isinstance(s, HybridStrategy) for s in strategies)


# ---------------------------------------------------------------------------
# run() — all-success tests
# ---------------------------------------------------------------------------


class TestRunAllSuccess:
    def _setup(self, queries):
        """Return an evaluator whose retrievers always return a matching doc."""
        ev = _make_evaluator(reranking_provider=None)
        hit_doc = _make_doc("勞動基準法", "第 24 條")
        ev.vector_retriever.search.return_value = [hit_doc]
        ev.bm25_retriever.search.return_value = [hit_doc]
        ev.hybrid_retriever.search.return_value = [hit_doc]
        ev.embedding_provider.embed_query.return_value = [0.1, 0.2]
        return ev

    def test_metrics_count_per_strategy_k_querytype(self):
        """run() should produce len(strategies) × len(k_values) × 3 StrategyMetrics."""
        queries = [
            _make_query(qt="semantic"),
            _make_query(qt="exact"),
        ]
        ev = self._setup(queries)
        strategies = ev.build_strategies(rrf_k_values=[10], test_reranker=False)
        # 1 vector + 1 bm25 + 1 hybrid = 3 strategies
        k_values = [5, 10]
        result = ev.run(queries, strategies, k_values=k_values)

        expected_count = len(strategies) * len(k_values) * 3  # 3 query_types
        assert len(result.metrics) == expected_count

    def test_query_types_present(self):
        """Each strategy × k combination should have semantic, exact, and all metrics."""
        queries = [_make_query(qt="semantic"), _make_query(qt="exact")]
        ev = self._setup(queries)
        strategies = ev.build_strategies(rrf_k_values=[10], test_reranker=False)
        result = ev.run(queries, strategies, k_values=[5])

        for strategy in strategies:
            for qt in ["semantic", "exact", "all"]:
                matching = [
                    m for m in result.metrics
                    if m.strategy_name == strategy.name and m.k == 5 and m.query_type == qt
                ]
                assert len(matching) == 1, f"Missing metrics for {strategy.name} k=5 qt={qt}"

    def test_no_errors_on_all_success(self):
        """No errors should be recorded when all retrievals succeed."""
        queries = [_make_query()]
        ev = self._setup(queries)
        strategies = ev.build_strategies(rrf_k_values=[10], test_reranker=False)
        result = ev.run(queries, strategies, k_values=[5])
        assert result.errors == []

    def test_success_count_equals_total_queries(self):
        """success_count for 'all' query_type should equal total queries when no failures."""
        queries = [_make_query(qt="semantic"), _make_query(qt="exact")]
        ev = self._setup(queries)
        strategies = [ev.build_strategies(rrf_k_values=[10], test_reranker=False)[0]]  # just vector
        result = ev.run(queries, strategies, k_values=[5])

        all_metrics = [m for m in result.metrics if m.query_type == "all" and m.k == 5]
        assert len(all_metrics) == 1
        assert all_metrics[0].success_count == 2
        assert all_metrics[0].failure_count == 0

    def test_timestamp_is_set(self):
        """EvaluationResult.timestamp should be a non-empty ISO string."""
        queries = [_make_query()]
        ev = self._setup(queries)
        strategies = ev.build_strategies(rrf_k_values=[10], test_reranker=False)
        result = ev.run(queries, strategies, k_values=[5])
        assert result.timestamp
        # Should be parseable as ISO datetime
        from datetime import datetime
        datetime.fromisoformat(result.timestamp)

    def test_total_queries_recorded(self):
        """EvaluationResult.total_queries should equal len(queries)."""
        queries = [_make_query(), _make_query(), _make_query()]
        ev = self._setup(queries)
        strategies = ev.build_strategies(rrf_k_values=[10], test_reranker=False)
        result = ev.run(queries, strategies, k_values=[5])
        assert result.total_queries == 3


# ---------------------------------------------------------------------------
# run() — partial failure tests
# ---------------------------------------------------------------------------


class TestRunPartialFailure:
    def test_errors_recorded_on_failure(self):
        """Errors should be recorded for each failing retrieval."""
        queries = [
            _make_query(query="good query", qt="semantic"),
            _make_query(query="bad query", qt="semantic"),
        ]
        ev = _make_evaluator(reranking_provider=None)
        hit_doc = _make_doc("勞動基準法", "第 24 條")

        def side_effect(query, top_k):
            if query == "bad query":
                raise RuntimeError("retrieval failed")
            return [hit_doc]

        ev.bm25_retriever.search.side_effect = side_effect
        ev.vector_retriever.search.return_value = [hit_doc]
        ev.hybrid_retriever.search.return_value = [hit_doc]
        ev.embedding_provider.embed_query.return_value = [0.1]

        bm25_strategy = BM25OnlyStrategy(ev.bm25_retriever)
        result = ev.run(queries, [bm25_strategy], k_values=[5])

        assert len(result.errors) == 1
        assert result.errors[0]["query"] == "bad query"
        assert result.errors[0]["strategy"] == "bm25"
        assert "retrieval failed" in result.errors[0]["error"]

    def test_success_plus_failure_equals_total(self):
        """success_count + failure_count should equal total queries for 'all' type."""
        queries = [
            _make_query(query="q1", qt="semantic"),
            _make_query(query="q2", qt="semantic"),
            _make_query(query="q3", qt="semantic"),
        ]
        ev = _make_evaluator(reranking_provider=None)
        hit_doc = _make_doc("勞動基準法", "第 24 條")
        call_count = {"n": 0}

        def side_effect(query, top_k):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("fail")
            return [hit_doc]

        ev.bm25_retriever.search.side_effect = side_effect
        bm25_strategy = BM25OnlyStrategy(ev.bm25_retriever)
        result = ev.run(queries, [bm25_strategy], k_values=[5])

        all_metrics = [m for m in result.metrics if m.query_type == "all" and m.k == 5]
        assert len(all_metrics) == 1
        m = all_metrics[0]
        assert m.success_count + m.failure_count == len(queries)

    def test_evaluation_continues_after_failure(self):
        """Evaluation should not stop when one query fails; remaining queries are processed."""
        queries = [
            _make_query(query="fail", qt="semantic"),
            _make_query(query="ok", qt="semantic"),
        ]
        ev = _make_evaluator(reranking_provider=None)
        hit_doc = _make_doc("勞動基準法", "第 24 條")

        def side_effect(query, top_k):
            if query == "fail":
                raise ValueError("boom")
            return [hit_doc]

        ev.bm25_retriever.search.side_effect = side_effect
        bm25_strategy = BM25OnlyStrategy(ev.bm25_retriever)
        result = ev.run(queries, [bm25_strategy], k_values=[5])

        # Should have 1 error and 1 success
        assert len(result.errors) == 1
        all_metrics = [m for m in result.metrics if m.query_type == "all" and m.k == 5]
        assert all_metrics[0].success_count == 1
        assert all_metrics[0].failure_count == 1

    def test_all_failures_produces_zero_metrics(self):
        """When all queries fail, metrics should be 0.0 with failure_count == total."""
        queries = [_make_query(qt="semantic"), _make_query(qt="exact")]
        ev = _make_evaluator(reranking_provider=None)
        ev.bm25_retriever.search.side_effect = RuntimeError("always fails")

        bm25_strategy = BM25OnlyStrategy(ev.bm25_retriever)
        result = ev.run(queries, [bm25_strategy], k_values=[5])

        all_metrics = [m for m in result.metrics if m.query_type == "all" and m.k == 5]
        assert len(all_metrics) == 1
        m = all_metrics[0]
        assert m.recall == 0.0
        assert m.mrr == 0.0
        assert m.ndcg == 0.0
        assert m.failure_count == 2
        assert m.success_count == 0
