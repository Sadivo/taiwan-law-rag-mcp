"""Evaluator and RetrievalStrategy implementations for the evaluation pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from evaluation.metrics import MetricsCalculator
from evaluation.models import EvalQuery, EvaluationResult, StrategyMetrics


# ---------------------------------------------------------------------------
# Strategy base class and concrete implementations
# ---------------------------------------------------------------------------


class RetrievalStrategy(ABC):
    """Abstract base class for retrieval strategies."""

    name: str

    @abstractmethod
    def retrieve(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Retrieve documents for the given query."""
        ...


class VectorOnlyStrategy(RetrievalStrategy):
    """Retrieval strategy using vector search only."""

    def __init__(self, embedding_provider: Any, vector_retriever: Any) -> None:
        self.name = "vector"
        self.embedding_provider = embedding_provider
        self.vector_retriever = vector_retriever

    def retrieve(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        vector = self.embedding_provider.embed_query(query)
        return self.vector_retriever.search(vector, top_k)


class BM25OnlyStrategy(RetrievalStrategy):
    """Retrieval strategy using BM25 search only."""

    def __init__(self, bm25_retriever: Any) -> None:
        self.name = "bm25"
        self.bm25_retriever = bm25_retriever

    def retrieve(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        return self.bm25_retriever.search(query, top_k)


class HybridStrategy(RetrievalStrategy):
    """Retrieval strategy using hybrid (vector + BM25) search with optional reranking."""

    def __init__(
        self,
        hybrid_retriever: Any,
        rrf_k: int,
        use_reranker: bool = False,
        reranking_provider: Optional[Any] = None,
    ) -> None:
        suffix = "_reranked" if use_reranker and reranking_provider is not None else ""
        self.name = f"hybrid_rrf{rrf_k}{suffix}"
        self.hybrid_retriever = hybrid_retriever
        self.rrf_k = rrf_k
        self.use_reranker = use_reranker
        self.reranking_provider = reranking_provider

    def retrieve(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        # Set rrf_k on the retriever if possible
        if hasattr(self.hybrid_retriever, "rrf_k"):
            self.hybrid_retriever.rrf_k = self.rrf_k

        results = self.hybrid_retriever.search(query, top_k)

        if self.use_reranker and self.reranking_provider is not None:
            results = self.reranking_provider.rerank(query, results, top_k)

        return results


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


class Evaluator:
    """Orchestrates multi-strategy evaluation over a Golden Dataset."""

    def __init__(
        self,
        embedding_provider: Optional[Any],
        reranking_provider: Optional[Any],
        vector_retriever: Any,
        bm25_retriever: Any,
        hybrid_retriever: Any,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.reranking_provider = reranking_provider
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.hybrid_retriever = hybrid_retriever

    def build_strategies(
        self,
        rrf_k_values: List[int] = [10, 30, 60],
        test_reranker: bool = True,
    ) -> List[RetrievalStrategy]:
        """Build all retrieval strategies to be evaluated."""
        strategies: List[RetrievalStrategy] = []

        # Vector-only
        strategies.append(
            VectorOnlyStrategy(self.embedding_provider, self.vector_retriever)
        )

        # BM25-only
        strategies.append(BM25OnlyStrategy(self.bm25_retriever))

        # Hybrid without reranker
        for k in rrf_k_values:
            strategies.append(
                HybridStrategy(
                    self.hybrid_retriever,
                    rrf_k=k,
                    use_reranker=False,
                )
            )

        # Hybrid with reranker
        if test_reranker and self.reranking_provider is not None:
            for k in rrf_k_values:
                strategies.append(
                    HybridStrategy(
                        self.hybrid_retriever,
                        rrf_k=k,
                        use_reranker=True,
                        reranking_provider=self.reranking_provider,
                    )
                )

        return strategies

    def run(
        self,
        queries: List[EvalQuery],
        strategies: List[RetrievalStrategy],
        k_values: List[int] = [5, 10],
    ) -> EvaluationResult:
        """Run evaluation for every strategy × k_value × query_type combination."""
        embedding_name = (
            type(self.embedding_provider).__name__
            if self.embedding_provider is not None
            else "none"
        )
        reranking_name = (
            type(self.reranking_provider).__name__
            if self.reranking_provider is not None
            else "none"
        )

        result = EvaluationResult(
            timestamp=datetime.now().isoformat(),
            embedding_provider=embedding_name,
            reranking_provider=reranking_name,
            total_queries=len(queries),
        )

        max_k = max(k_values) if k_values else 10

        for strategy in strategies:
            # Collect per-query results (results, expected_keys, query_type, success/fail)
            per_query: List[Dict[str, Any]] = []

            for q in queries:
                expected_keys = [
                    f"{q.expected_law}:{art}" for art in q.expected_articles
                ]
                try:
                    docs = strategy.retrieve(q.query, top_k=max_k)
                    per_query.append(
                        {
                            "docs": docs,
                            "expected": expected_keys,
                            "query_type": q.query_type,
                            "success": True,
                        }
                    )
                except Exception as exc:
                    result.errors.append(
                        {
                            "query": q.query,
                            "strategy": strategy.name,
                            "error": str(exc),
                        }
                    )
                    per_query.append(
                        {
                            "docs": None,
                            "expected": expected_keys,
                            "query_type": q.query_type,
                            "success": False,
                        }
                    )

            # Compute metrics for each k_value × query_type
            query_types = ["semantic", "exact", "all"]

            for k in k_values:
                for qt in query_types:
                    subset = [
                        pq
                        for pq in per_query
                        if qt == "all" or pq["query_type"] == qt
                    ]

                    success_items = [pq for pq in subset if pq["success"]]
                    failure_count = len(subset) - len(success_items)

                    if not success_items:
                        result.metrics.append(
                            StrategyMetrics(
                                strategy_name=strategy.name,
                                k=k,
                                recall=0.0,
                                mrr=0.0,
                                ndcg=0.0,
                                query_type=qt,
                                success_count=0,
                                failure_count=failure_count,
                            )
                        )
                        continue

                    # Recall@K — average over queries
                    recall_scores = [
                        MetricsCalculator.recall_at_k(pq["docs"], pq["expected"], k)
                        for pq in success_items
                    ]
                    avg_recall = sum(recall_scores) / len(recall_scores)

                    # MRR — across all successful queries in subset
                    results_list = [pq["docs"] for pq in success_items]
                    expected_list = [pq["expected"] for pq in success_items]
                    mrr_score = MetricsCalculator.mrr(results_list, expected_list)

                    # NDCG@K — average over queries
                    ndcg_scores = [
                        MetricsCalculator.ndcg_at_k(pq["docs"], pq["expected"], k)
                        for pq in success_items
                    ]
                    avg_ndcg = sum(ndcg_scores) / len(ndcg_scores)

                    result.metrics.append(
                        StrategyMetrics(
                            strategy_name=strategy.name,
                            k=k,
                            recall=avg_recall,
                            mrr=mrr_score,
                            ndcg=avg_ndcg,
                            query_type=qt,
                            success_count=len(success_items),
                            failure_count=failure_count,
                        )
                    )

        return result
