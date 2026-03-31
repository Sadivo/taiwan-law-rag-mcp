"""Report generator for evaluation pipeline results."""

import os
from datetime import datetime
from typing import Optional

from evaluation.exceptions import ReportWriteError
from evaluation.models import EvaluationResult, StrategyMetrics


class ReportGenerator:
    """Generates Markdown evaluation reports from EvaluationResult."""

    def generate(
        self,
        result: EvaluationResult,
        output_dir: str = "data/eval/results",
    ) -> str:
        """輸出報告至檔案，回傳儲存路徑"""
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"eval_{timestamp}.md"
        filepath = os.path.join(output_dir, filename)

        report = self._build_report(result)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report)
        except OSError as e:
            raise ReportWriteError(f"Failed to write report to {filepath}: {e}") from e

        return filepath

    def _build_report(self, result: EvaluationResult) -> str:
        """Build the full Markdown report string."""
        lines = []

        lines.append("# Evaluation Report\n")
        lines.append(f"**Timestamp:** {result.timestamp}\n")
        lines.append(f"**Embedding Provider:** {result.embedding_provider}\n")
        lines.append(f"**Reranking Provider:** {result.reranking_provider}\n")
        lines.append("")

        lines.append("## Strategy Comparison\n")
        lines.append(self._build_comparison_table(result))
        lines.append("")

        lines.append("## Recall@10 Bar Chart\n")
        lines.append(self._build_ascii_bar_chart(result, metric="recall@10"))
        lines.append("")

        # Summary
        success_count = sum(
            m.success_count
            for m in result.metrics
            if m.query_type == "all" and m.k == 10
        )
        failure_count = sum(
            m.failure_count
            for m in result.metrics
            if m.query_type == "all" and m.k == 10
        )

        lines.append("## Summary\n")
        lines.append(f"- **Total Queries:** {result.total_queries}")
        lines.append(f"- **Success:** {success_count}")
        lines.append(f"- **Failure:** {failure_count}")
        lines.append("")

        return "\n".join(lines)

    def _build_comparison_table(self, result: EvaluationResult) -> str:
        """建立 Markdown 比較表格，包含各策略的 Recall@5, Recall@10, MRR, NDCG@10"""
        # Collect unique strategy names (preserving order)
        strategy_names = []
        seen = set()
        for m in result.metrics:
            if m.strategy_name not in seen:
                strategy_names.append(m.strategy_name)
                seen.add(m.strategy_name)

        # Build lookup: (strategy_name, k, query_type) -> StrategyMetrics
        lookup: dict = {}
        for m in result.metrics:
            lookup[(m.strategy_name, m.k, m.query_type)] = m

        header = "| Strategy | Recall@5 | Recall@10 | MRR | NDCG@10 |"
        separator = "|---|---|---|---|---|"
        rows = [header, separator]

        for name in strategy_names:
            m5 = lookup.get((name, 5, "all"))
            m10 = lookup.get((name, 10, "all"))

            recall5 = f"{m5.recall:.4f}" if m5 else "N/A"
            recall10 = f"{m10.recall:.4f}" if m10 else "N/A"
            mrr = f"{m10.mrr:.4f}" if m10 else (f"{m5.mrr:.4f}" if m5 else "N/A")
            ndcg10 = f"{m10.ndcg:.4f}" if m10 else "N/A"

            rows.append(f"| {name} | {recall5} | {recall10} | {mrr} | {ndcg10} |")

        return "\n".join(rows)

    def _build_ascii_bar_chart(
        self, result: EvaluationResult, metric: str = "recall@10"
    ) -> str:
        """建立 ASCII 橫條圖，使用 █ 字元"""
        # Parse metric name to determine k and field
        metric_lower = metric.lower()
        if metric_lower == "recall@10":
            k, field = 10, "recall"
        elif metric_lower == "recall@5":
            k, field = 5, "recall"
        elif metric_lower == "mrr":
            k, field = 10, "mrr"
        elif metric_lower == "ndcg@10":
            k, field = 10, "ndcg"
        else:
            k, field = 10, "recall"

        # Collect (strategy_name, value) for query_type == "all"
        entries = []
        seen = set()
        for m in result.metrics:
            if m.query_type == "all" and m.k == k and m.strategy_name not in seen:
                value = getattr(m, field, 0.0)
                entries.append((m.strategy_name, value))
                seen.add(m.strategy_name)

        if not entries:
            return ""

        max_bar_width = 40
        lines = []
        for name, value in entries:
            filled = round(value * max_bar_width)
            bar = "█" * filled + "░" * (max_bar_width - filled)
            lines.append(f"{name} | {bar} {value:.2f}")

        return "\n".join(lines)
