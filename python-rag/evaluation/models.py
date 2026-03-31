"""Data models for the evaluation pipeline."""

from dataclasses import dataclass, field
from typing import Dict, List, Literal


@dataclass
class EvalQuery:
    """A single evaluation item from the Golden Dataset."""

    query: str
    expected_law: str
    expected_articles: List[str]
    query_type: Literal["semantic", "exact"]
    notes: str = ""


@dataclass
class StrategyMetrics:
    """Metrics for a single retrieval strategy at a given K value."""

    strategy_name: str
    k: int
    recall: float        # Recall@K
    mrr: float           # MRR (recorded per strategy)
    ndcg: float          # NDCG@K
    query_type: str      # "semantic" | "exact" | "all"
    success_count: int
    failure_count: int


@dataclass
class EvaluationResult:
    """Complete result of an evaluation run."""

    timestamp: str                          # ISO 8601 format
    embedding_provider: str
    reranking_provider: str
    total_queries: int
    metrics: List[StrategyMetrics] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)
