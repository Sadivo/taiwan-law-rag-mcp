"""Unit tests for ReportGenerator."""

import os
import re
import tempfile

import pytest

from evaluation.exceptions import ReportWriteError
from evaluation.models import EvaluationResult, StrategyMetrics
from evaluation.report import ReportGenerator


def make_result(
    embedding_provider: str = "test-embed",
    reranking_provider: str = "test-rerank",
    total_queries: int = 10,
) -> EvaluationResult:
    """Build a minimal EvaluationResult for testing."""
    metrics = [
        StrategyMetrics(
            strategy_name="vector",
            k=5,
            recall=0.6,
            mrr=0.5,
            ndcg=0.55,
            query_type="all",
            success_count=9,
            failure_count=1,
        ),
        StrategyMetrics(
            strategy_name="vector",
            k=10,
            recall=0.75,
            mrr=0.5,
            ndcg=0.65,
            query_type="all",
            success_count=9,
            failure_count=1,
        ),
        StrategyMetrics(
            strategy_name="bm25",
            k=5,
            recall=0.5,
            mrr=0.4,
            ndcg=0.45,
            query_type="all",
            success_count=8,
            failure_count=2,
        ),
        StrategyMetrics(
            strategy_name="bm25",
            k=10,
            recall=0.65,
            mrr=0.4,
            ndcg=0.55,
            query_type="all",
            success_count=8,
            failure_count=2,
        ),
    ]
    return EvaluationResult(
        timestamp="2024-01-01T00:00:00",
        embedding_provider=embedding_provider,
        reranking_provider=reranking_provider,
        total_queries=total_queries,
        metrics=metrics,
        errors=[],
    )


class TestReportGeneratorOutputDir:
    def test_auto_creates_output_dir(self):
        """Output directory is created automatically when it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "nested", "results")
            assert not os.path.exists(output_dir)

            gen = ReportGenerator()
            path = gen.generate(make_result(), output_dir=output_dir)

            assert os.path.isdir(output_dir)
            assert os.path.isfile(path)

    def test_existing_output_dir_does_not_raise(self):
        """generate() works fine when output_dir already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator()
            path = gen.generate(make_result(), output_dir=tmpdir)
            assert os.path.isfile(path)


class TestReportFilename:
    def test_filename_matches_timestamp_pattern(self):
        """Filename must match eval_YYYYMMDD_HHMMSS.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator()
            path = gen.generate(make_result(), output_dir=tmpdir)
            filename = os.path.basename(path)
            pattern = r"^eval_\d{8}_\d{6}\.md$"
            assert re.match(pattern, filename), f"Filename '{filename}' does not match pattern"

    def test_generate_returns_string_path(self):
        """generate() returns a string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator()
            path = gen.generate(make_result(), output_dir=tmpdir)
            assert isinstance(path, str)


class TestReportContent:
    def _read_report(self, result: EvaluationResult) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReportGenerator()
            path = gen.generate(result, output_dir=tmpdir)
            with open(path, encoding="utf-8") as f:
                return f.read()

    def test_report_contains_table_separator(self):
        """Report must contain | for Markdown table."""
        content = self._read_report(make_result())
        assert "|" in content

    def test_report_contains_bar_chart_character(self):
        """Report must contain █ for ASCII bar chart."""
        content = self._read_report(make_result())
        assert "█" in content

    def test_report_contains_embedding_provider(self):
        """Report must include embedding provider name."""
        result = make_result(embedding_provider="my-embed-provider")
        content = self._read_report(result)
        assert "my-embed-provider" in content

    def test_report_contains_reranking_provider(self):
        """Report must include reranking provider name."""
        result = make_result(reranking_provider="my-rerank-provider")
        content = self._read_report(result)
        assert "my-rerank-provider" in content

    def test_report_contains_total_queries(self):
        """Report must include total_queries count."""
        result = make_result(total_queries=42)
        content = self._read_report(result)
        assert "42" in content

    def test_report_contains_success_and_failure_counts(self):
        """Report must include success and failure counts."""
        content = self._read_report(make_result())
        assert "Success" in content or "success" in content.lower()
        assert "Failure" in content or "failure" in content.lower()

    def test_comparison_table_has_strategy_names(self):
        """Comparison table rows include strategy names."""
        content = self._read_report(make_result())
        assert "vector" in content
        assert "bm25" in content

    def test_bar_chart_has_strategy_names(self):
        """ASCII bar chart includes strategy names."""
        gen = ReportGenerator()
        result = make_result()
        chart = gen._build_ascii_bar_chart(result)
        assert "vector" in chart
        assert "bm25" in chart


class TestReportWriteError:
    def test_raises_report_write_error_on_invalid_path(self):
        """ReportWriteError is raised when the file cannot be written."""
        from unittest.mock import patch

        gen = ReportGenerator()
        result = make_result()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch open() to simulate a write failure
            with patch("builtins.open", side_effect=OSError("disk full")):
                with pytest.raises(ReportWriteError) as exc_info:
                    gen.generate(result, output_dir=tmpdir)
            assert tmpdir in str(exc_info.value)
