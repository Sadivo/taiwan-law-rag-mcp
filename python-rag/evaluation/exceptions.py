"""Custom exceptions for the evaluation pipeline."""


class EvaluationPipelineError(Exception):
    """Base exception for all evaluation pipeline errors."""


class DatasetNotFoundError(EvaluationPipelineError):
    """Raised when the golden dataset file cannot be found."""


class DatasetFormatError(EvaluationPipelineError):
    """Raised when the dataset file cannot be parsed (e.g. invalid JSON)."""


class DatasetValidationError(EvaluationPipelineError):
    """Raised when the dataset fails schema validation."""


class ReportWriteError(EvaluationPipelineError):
    """Raised when the evaluation report cannot be written to disk."""
