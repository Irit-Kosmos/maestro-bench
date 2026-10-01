"""
Compute an analysis: metrics with bootstrap confidence intervals for one or
more executions, each compared independently against the same ground truth.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from analysis.bootstrap import bootstrap_ci
from analysis.extract import ExcludedRow, Extraction, ValueType, extract_pairs
from analysis.metrics import METRICS, Undefined, sort_labels

LOW_COVERAGE_THRESHOLD = 0.9


@dataclass
class AnalysisConfig:
    truth_column: str
    output_path: str
    value_type: ValueType
    metrics: list[str]
    ignore_case: bool = False
    n_boot: int = 1000
    confidence: float = 0.95
    seed: int = 0


@dataclass
class RunInput:
    """One execution to analyse: its result rows and the agent to read."""

    label: str
    agent_name: str
    rows: list[dict]
    execution_id: int | None = None
    # Dataset snapshot of the execution (file path and sampling), used to warn
    # when runs are not computed on the same data
    dataset: dict | None = None


@dataclass
class MetricValue:
    value: float | None
    ci_low: float | None = None
    ci_high: float | None = None
    undefined_reason: str | None = None


@dataclass
class RunResult:
    label: str
    agent_name: str
    execution_id: int | None
    n_valid: int
    n_total: int
    metrics: dict[str, MetricValue]
    exclusions: dict[str, int]
    excluded_rows: list[ExcludedRow]
    warnings: list[str] = field(default_factory=list)
    # Numeric: predicted vs actual pairs
    points: list[dict[str, Any]] | None = None
    # Categorical: confusion matrix, rows = truth, columns = prediction
    confusion: dict[str, Any] | None = None

    @property
    def coverage(self) -> float | None:
        return self.n_valid / self.n_total if self.n_total else None


@dataclass
class AnalysisResult:
    runs: list[RunResult]
    warnings: list[str]


def validate_config(config: AnalysisConfig) -> None:
    """Raise ValueError when the configuration cannot be computed."""
    if not config.metrics:
        raise ValueError("Select at least one metric")
    for key in config.metrics:
        metric = METRICS.get(key)
        if metric is None:
            raise ValueError(f"Unknown metric '{key}'")
        if metric.kind != config.value_type:
            raise ValueError(
                f"Metric '{key}' is {metric.kind}, the analysis is {config.value_type}"
            )
    if not 0 < config.confidence < 1:
        raise ValueError("Confidence must be between 0 and 1")
    if config.n_boot < 0:
        raise ValueError("Bootstrap resamples must be positive")


def compute_analysis(config: AnalysisConfig, runs: list[RunInput]) -> AnalysisResult:
    validate_config(config)
    return AnalysisResult(
        runs=[compute_run(config, run) for run in runs],
        warnings=comparison_warnings(runs),
    )


def compute_run(config: AnalysisConfig, run: RunInput) -> RunResult:
    extraction = extract_pairs(
        run.rows,
        agent_name=run.agent_name,
        output_path=config.output_path,
        truth_column=config.truth_column,
        value_type=config.value_type,
        ignore_case=config.ignore_case,
    )

    if config.value_type == "numeric":
        statistics, points, confusion = _numeric(config, extraction)
    else:
        statistics, points, confusion = _categorical(config, extraction)

    n = extraction.n_valid
    estimates = statistics(np.arange(n))
    intervals = bootstrap_ci(
        lambda indices: {k: v for k, (v, _) in statistics(indices).items()},
        n=n,
        n_boot=config.n_boot,
        confidence=config.confidence,
        seed=config.seed,
    )

    metrics: dict[str, MetricValue] = {}
    for key, (value, reason) in estimates.items():
        interval = intervals.get(key) if value is not None else None
        metrics[key] = MetricValue(
            value=value,
            ci_low=interval[0] if interval else None,
            ci_high=interval[1] if interval else None,
            undefined_reason=reason,
        )

    result = RunResult(
        label=run.label,
        agent_name=run.agent_name,
        execution_id=run.execution_id,
        n_valid=n,
        n_total=extraction.n_total,
        metrics=metrics,
        exclusions=dict(Counter(row.reason.value for row in extraction.excluded)),
        excluded_rows=extraction.excluded,
        points=points,
        confusion=confusion,
    )
    if result.coverage is not None and result.coverage < LOW_COVERAGE_THRESHOLD:
        result.warnings.append(
            f"Only {result.coverage:.0%} of rows could be used "
            f"({result.n_valid}/{result.n_total})"
        )
    if result.n_total == 0:
        result.warnings.append("The execution has no result rows")
    return result


# A statistics function maps resampled row indices to {key: (value, reason)}
# where value is None when the metric is undefined on those rows.
Statistics = dict[str, tuple[float | None, str | None]]


def _evaluate(fn, *args) -> tuple[float | None, str | None]:
    try:
        return fn(*args), None
    except Undefined as e:
        return None, str(e)


def _numeric(config: AnalysisConfig, extraction: Extraction):
    pred = np.asarray(extraction.predictions, dtype=float)
    truth = np.asarray(extraction.truths, dtype=float)

    def statistics(indices: np.ndarray) -> Statistics:
        p, t = pred[indices], truth[indices]
        if len(indices) == 0:
            return {key: (None, "No usable rows") for key in config.metrics}
        return {key: _evaluate(METRICS[key].fn, p, t) for key in config.metrics}

    points = [
        {"pred": p, "truth": t, "row_index": i}
        for p, t, i in zip(
            extraction.predictions,
            extraction.truths,
            extraction.row_indices,
            strict=True,
        )
    ]
    return statistics, points, None


def _categorical(config: AnalysisConfig, extraction: Extraction):
    labels = sort_labels(set(extraction.truths) | set(extraction.predictions))
    code = {label: i for i, label in enumerate(labels)}
    k = len(labels)
    truth = np.array([code[t] for t in extraction.truths], dtype=int)
    pred = np.array([code[p] for p in extraction.predictions], dtype=int)

    def confusion_matrix(indices: np.ndarray) -> np.ndarray:
        cells = truth[indices] * k + pred[indices]
        return np.bincount(cells, minlength=k * k).reshape(k, k)

    def statistics(indices: np.ndarray) -> Statistics:
        if len(indices) == 0:
            return {key: (None, "No usable rows") for key in config.metrics}
        cm = confusion_matrix(indices)
        return {key: _evaluate(METRICS[key].fn, cm, labels) for key in config.metrics}

    confusion = {
        "labels": labels,
        "matrix": confusion_matrix(np.arange(len(truth))).tolist(),
    }
    return statistics, None, confusion


def comparison_warnings(runs: list[RunInput]) -> list[str]:
    """Flag comparisons made on different datasets or different samples."""
    snapshots = [run.dataset for run in runs if run.dataset]
    if len(snapshots) < 2:
        return []

    warnings = []
    if len({s.get("file_path") for s in snapshots}) > 1:
        warnings.append("Runs use different datasets")
    elif len({_sampling_key(s) for s in snapshots}) > 1 or any(
        _is_unseeded_random(s) for s in snapshots
    ):
        warnings.append("Runs use different samples of the dataset")
    return warnings


def _sampling_key(snapshot: dict) -> tuple:
    sampling = snapshot.get("sampling_config") or {}
    sampling_type = sampling.get("sampling_type") or "all"
    if sampling_type == "random":
        return (
            sampling_type,
            sampling.get("sampling_size"),
            sampling.get("sampling_seed"),
        )
    if sampling_type == "range":
        return (
            sampling_type,
            sampling.get("sampling_start_row"),
            sampling.get("sampling_end_row"),
        )
    return (sampling_type,)


def _is_unseeded_random(snapshot: dict) -> bool:
    sampling = snapshot.get("sampling_config") or {}
    return (
        sampling.get("sampling_type") == "random"
        and sampling.get("sampling_seed") is None
    )
