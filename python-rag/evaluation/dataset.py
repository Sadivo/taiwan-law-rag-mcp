"""Dataset loader for the evaluation pipeline."""

import json
import os
from typing import List, Optional

import jsonschema

from evaluation.exceptions import (
    DatasetFormatError,
    DatasetNotFoundError,
    DatasetValidationError,
)
from evaluation.models import EvalQuery

_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["query", "expected_law", "expected_articles", "query_type"],
        "properties": {
            "query":             {"type": "string", "minLength": 1},
            "expected_law":      {"type": "string", "minLength": 1},
            "expected_articles": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "query_type":        {"type": "string", "enum": ["semantic", "exact"]},
            "notes":             {"type": "string"},
        },
        "additionalProperties": False,
    },
}


class DatasetLoader:
    """Loads and validates the Golden Dataset for evaluation."""

    def load(self, path: str) -> List[EvalQuery]:
        """Read JSON file, validate against schema, return list of EvalQuery.

        Raises:
            DatasetNotFoundError: when the file does not exist.
            DatasetFormatError: when JSON parsing fails.
            DatasetValidationError: when schema validation fails.
        """
        if not os.path.exists(path):
            raise DatasetNotFoundError(f"Dataset file not found: {os.path.abspath(path)}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise DatasetFormatError(
                f"Failed to parse JSON at line {exc.lineno}: {exc.msg}"
            ) from exc

        try:
            jsonschema.validate(data, _SCHEMA)
        except jsonschema.ValidationError as exc:
            # Build a descriptive message with field name and index
            path_parts = list(exc.absolute_path)
            if path_parts:
                index = path_parts[0] if isinstance(path_parts[0], int) else None
                field = path_parts[-1] if len(path_parts) > 1 else None
                if index is not None and field is not None:
                    msg = f"Validation error at index {index}, field '{field}': {exc.message}"
                elif index is not None:
                    msg = f"Validation error at index {index}: {exc.message}"
                else:
                    msg = f"Validation error at field '{path_parts[-1]}': {exc.message}"
            else:
                msg = f"Validation error: {exc.message}"
            raise DatasetValidationError(msg) from exc

        return [
            EvalQuery(
                query=item["query"],
                expected_law=item["expected_law"],
                expected_articles=list(item["expected_articles"]),
                query_type=item["query_type"],
                notes=item.get("notes", ""),
            )
            for item in data
        ]

    def filter_by_type(
        self, queries: List[EvalQuery], query_type: Optional[str]
    ) -> List[EvalQuery]:
        """Filter queries by query_type ('semantic' or 'exact').

        If query_type is None, returns all queries unchanged.
        """
        if query_type is None:
            return list(queries)
        return [q for q in queries if q.query_type == query_type]
