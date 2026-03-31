"""Unit tests for evaluation/dataset.py — DatasetLoader."""

import json
import os
import sys

import pytest

# Ensure python-rag is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evaluation.dataset import DatasetLoader
from evaluation.exceptions import (
    DatasetFormatError,
    DatasetNotFoundError,
    DatasetValidationError,
)
from evaluation.models import EvalQuery

VALID_ITEM = {
    "query": "加班費如何計算",
    "expected_law": "勞動基準法",
    "expected_articles": ["第 24 條"],
    "query_type": "semantic",
}


@pytest.fixture
def loader():
    return DatasetLoader()


@pytest.fixture
def tmp_json(tmp_path):
    """Helper: write data to a temp JSON file and return its path."""
    def _write(data):
        p = tmp_path / "dataset.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return str(p)
    return _write


# ── File-not-found ────────────────────────────────────────────────────────────

def test_file_not_found_raises_with_path(loader, tmp_path):
    missing = str(tmp_path / "no_such_file.json")
    with pytest.raises(DatasetNotFoundError) as exc_info:
        loader.load(missing)
    assert "no_such_file.json" in str(exc_info.value)


# ── Invalid JSON ──────────────────────────────────────────────────────────────

def test_invalid_json_raises_format_error(loader, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(DatasetFormatError):
        loader.load(str(bad))


# ── Schema validation ─────────────────────────────────────────────────────────

def test_missing_required_field_raises_validation_error(loader, tmp_json):
    item = {k: v for k, v in VALID_ITEM.items() if k != "query"}
    path = tmp_json([item])
    with pytest.raises(DatasetValidationError) as exc_info:
        loader.load(path)
    assert "query" in str(exc_info.value)


def test_missing_expected_law_raises_validation_error(loader, tmp_json):
    item = {k: v for k, v in VALID_ITEM.items() if k != "expected_law"}
    path = tmp_json([item])
    with pytest.raises(DatasetValidationError) as exc_info:
        loader.load(path)
    assert "expected_law" in str(exc_info.value)


def test_invalid_query_type_raises_validation_error(loader, tmp_json):
    item = {**VALID_ITEM, "query_type": "unknown"}
    path = tmp_json([item])
    with pytest.raises(DatasetValidationError):
        loader.load(path)


def test_empty_articles_array_raises_validation_error(loader, tmp_json):
    item = {**VALID_ITEM, "expected_articles": []}
    path = tmp_json([item])
    with pytest.raises(DatasetValidationError):
        loader.load(path)


# ── Successful loads ──────────────────────────────────────────────────────────

def test_empty_list_loads_successfully(loader, tmp_json):
    path = tmp_json([])
    result = loader.load(path)
    assert result == []


def test_valid_single_item_loads(loader, tmp_json):
    path = tmp_json([VALID_ITEM])
    result = loader.load(path)
    assert len(result) == 1
    q = result[0]
    assert isinstance(q, EvalQuery)
    assert q.query == VALID_ITEM["query"]
    assert q.expected_law == VALID_ITEM["expected_law"]
    assert q.expected_articles == VALID_ITEM["expected_articles"]
    assert q.query_type == "semantic"
    assert q.notes == ""


def test_optional_notes_field(loader, tmp_json):
    item = {**VALID_ITEM, "notes": "some note"}
    path = tmp_json([item])
    result = loader.load(path)
    assert result[0].notes == "some note"


# ── filter_by_type ────────────────────────────────────────────────────────────

def _make_queries():
    return [
        EvalQuery("q1", "法律A", ["第1條"], "semantic"),
        EvalQuery("q2", "法律B", ["第2條"], "exact"),
        EvalQuery("q3", "法律C", ["第3條"], "semantic"),
        EvalQuery("q4", "法律D", ["第4條"], "exact"),
    ]


def test_filter_by_type_semantic(loader):
    queries = _make_queries()
    result = loader.filter_by_type(queries, "semantic")
    assert all(q.query_type == "semantic" for q in result)
    assert len(result) == 2


def test_filter_by_type_exact(loader):
    queries = _make_queries()
    result = loader.filter_by_type(queries, "exact")
    assert all(q.query_type == "exact" for q in result)
    assert len(result) == 2


def test_filter_by_type_none_returns_all(loader):
    queries = _make_queries()
    result = loader.filter_by_type(queries, None)
    assert len(result) == len(queries)


def test_filter_result_length_not_exceeds_original(loader):
    queries = _make_queries()
    for qt in ("semantic", "exact"):
        result = loader.filter_by_type(queries, qt)
        assert len(result) <= len(queries)
