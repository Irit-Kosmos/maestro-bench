"""
Evaluation of execution results against a ground-truth column.

Pure computation: no web framework or database dependency, so it can be used
from the API, a script or a notebook.
"""

from analysis.compute import (
    AnalysisConfig,
    AnalysisResult,
    RunInput,
    RunResult,
    compute_analysis,
    validate_config,
)
from analysis.metrics import METRICS, Metric
from analysis.results import result_rows, row_count

__all__ = [
    "METRICS",
    "AnalysisConfig",
    "AnalysisResult",
    "Metric",
    "RunInput",
    "RunResult",
    "compute_analysis",
    "result_rows",
    "row_count",
    "validate_config",
]
