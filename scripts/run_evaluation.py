"""CLI entry point for the evaluation pipeline."""

import sys
import os

# Add python-rag to sys.path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python-rag'))

import argparse

from evaluation.dataset import DatasetLoader
from evaluation.exceptions import (
    DatasetNotFoundError,
    DatasetValidationError,
)
from evaluation.evaluator import Evaluator
from evaluation.report import ReportGenerator
from providers.config import (
    ProviderInitializationError,
    DimensionMismatchError,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run evaluation pipeline for Taiwan Law RAG system"
    )
    parser.add_argument(
        "--strategy",
        choices=["vector", "bm25", "hybrid", "all"],
        default="all",
        help="Retrieval strategy to evaluate (default: all)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=10,
        help="Top-K value for retrieval (default: 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate dataset only, no retrieval",
    )
    parser.add_argument(
        "--dataset",
        default="data/eval/golden_dataset.json",
        help="Path to golden dataset (default: data/eval/golden_dataset.json)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/eval/results",
        help="Output directory for reports (default: data/eval/results)",
    )
    return parser.parse_args()


def print_summary_table(result) -> None:
    """Print a summary table of evaluation results to the terminal."""
    # Collect unique strategy names
    strategy_names = []
    seen = set()
    for m in result.metrics:
        if m.strategy_name not in seen:
            strategy_names.append(m.strategy_name)
            seen.add(m.strategy_name)

    # Build lookup
    lookup = {}
    for m in result.metrics:
        lookup[(m.strategy_name, m.k, m.query_type)] = m

    print("\n=== Evaluation Summary ===")
    print(f"{'Strategy':<30} {'Recall@K':>10} {'MRR':>8} {'NDCG@K':>8}")
    print("-" * 60)
    for name in strategy_names:
        m = lookup.get((name, 10, "all")) or lookup.get((name, 5, "all"))
        if m:
            print(f"{name:<30} {m.recall:>10.4f} {m.mrr:>8.4f} {m.ndcg:>8.4f}")
    print("-" * 60)
    print(f"Total queries: {result.total_queries}")
    if result.errors:
        print(f"Errors: {len(result.errors)}")


def main() -> None:
    args = parse_args()

    # 1. Load dataset
    loader = DatasetLoader()
    try:
        queries = loader.load(args.dataset)
    except DatasetNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except DatasetValidationError as e:
        print(f"Dataset validation error: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Dry-run: print stats and exit
    if args.dry_run:
        semantic_count = sum(1 for q in queries if q.query_type == "semantic")
        exact_count = sum(1 for q in queries if q.query_type == "exact")
        print(f"Dataset: {args.dataset}")
        print(f"  Total queries : {len(queries)}")
        print(f"  Semantic      : {semantic_count}")
        print(f"  Exact         : {exact_count}")
        print("Dataset validation passed.")
        sys.exit(0)

    # 3. Initialize providers and retrievers
    try:
        from providers.factory import ProviderFactory
        from retrieval.vector_retriever import VectorRetriever
        from retrieval.bm25_retriever import BM25Retriever
        from retrieval.hybrid_retriever import HybridRetriever

        embedding_provider, reranking_provider = ProviderFactory.from_env()

        vector_retriever = VectorRetriever(
            index_path="data/taiwan_law.faiss",
            meta_path="data/chunks.pkl",
        )
        bm25_retriever = BM25Retriever(index_dir="data/bm25_index")
        hybrid_retriever = HybridRetriever(
            vector_retriever,
            bm25_retriever,
            embedder=embedding_provider,
        )
    except ProviderInitializationError as e:
        print(f"Provider initialization error: {e}", file=sys.stderr)
        sys.exit(1)
    except DimensionMismatchError as e:
        print(f"Dimension mismatch error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Initialization error: {e}", file=sys.stderr)
        sys.exit(1)

    # 4. Create evaluator and build strategies
    evaluator = Evaluator(
        embedding_provider=embedding_provider,
        reranking_provider=reranking_provider,
        vector_retriever=vector_retriever,
        bm25_retriever=bm25_retriever,
        hybrid_retriever=hybrid_retriever,
    )

    strategies = evaluator.build_strategies()

    # Filter strategies if --strategy is specified
    if args.strategy != "all":
        strategies = [s for s in strategies if s.name.startswith(args.strategy)]
        if not strategies:
            print(f"Error: No strategies found matching '{args.strategy}'", file=sys.stderr)
            sys.exit(1)

    k_values = [args.k]

    # 5. Run evaluation
    print(f"Running evaluation with {len(strategies)} strategy/strategies, k={args.k}...")
    result = evaluator.run(queries, strategies, k_values=k_values)

    # 6. Generate report
    report_path = ReportGenerator().generate(result, output_dir=args.output_dir)

    # 7. Print summary and report path
    print_summary_table(result)
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
