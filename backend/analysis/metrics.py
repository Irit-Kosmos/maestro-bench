"""
Metric registry.

Numeric metrics take ``(pred, truth)`` float arrays. Categorical metrics take a
confusion matrix (rows = truth, columns = prediction) and its labels, which
keeps bootstrap resampling cheap: a resample only needs a new matrix.

A metric raises ``Undefined`` when it has no meaningful value (a correlation
on constant data, a kappa with a single class); it is then reported as missing,
never as 0.

To add a metric, write a function and decorate it with ``@numeric`` or
``@categorical``.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np

MetricKind = Literal["numeric", "categorical"]


class Undefined(Exception):
    """The metric has no value for this data; the message says why."""


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    kind: MetricKind
    description: str
    fn: Callable[..., float]
    # Whether lower values are better; lets the UI highlight the best run
    lower_is_better: bool = False


METRICS: dict[str, Metric] = {}


def _register(kind: MetricKind, key: str, label: str, lower_is_better: bool):
    def decorator(fn: Callable[..., float]) -> Callable[..., float]:
        METRICS[key] = Metric(
            key=key,
            label=label,
            kind=kind,
            description=(fn.__doc__ or "").strip(),
            fn=fn,
            lower_is_better=lower_is_better,
        )
        return fn

    return decorator


def numeric(key: str, label: str, lower_is_better: bool = False):
    return _register("numeric", key, label, lower_is_better)


def categorical(key: str, label: str, lower_is_better: bool = False):
    return _register("categorical", key, label, lower_is_better)


# ---------------------------------------------------------------------------
# Numeric
# ---------------------------------------------------------------------------


@numeric("rmse", "RMSE", lower_is_better=True)
def rmse(pred: np.ndarray, truth: np.ndarray) -> float:
    """Root mean squared error."""
    return float(np.sqrt(np.mean((pred - truth) ** 2)))


@numeric("mae", "MAE", lower_is_better=True)
def mae(pred: np.ndarray, truth: np.ndarray) -> float:
    """Mean absolute error."""
    return float(np.mean(np.abs(pred - truth)))


@numeric("bias", "Bias")
def bias(pred: np.ndarray, truth: np.ndarray) -> float:
    """Mean of prediction − truth. Positive: the model over-predicts."""
    return float(np.mean(pred - truth))


@numeric("pearson", "Pearson r")
def pearson(pred: np.ndarray, truth: np.ndarray) -> float:
    """Pearson linear correlation."""
    return _correlation(pred, truth)


@numeric("spearman", "Spearman ρ")
def spearman(pred: np.ndarray, truth: np.ndarray) -> float:
    """Spearman rank correlation (ties get their average rank)."""
    return _correlation(_rank(pred), _rank(truth))


def _correlation(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        raise Undefined("Needs at least 2 rows")
    x_centered = x - x.mean()
    y_centered = y - y.mean()
    denominator = np.sqrt(np.sum(x_centered**2) * np.sum(y_centered**2))
    if denominator == 0:
        raise Undefined("Constant values: correlation is undefined")
    return float(np.sum(x_centered * y_centered) / denominator)


def _rank(values: np.ndarray) -> np.ndarray:
    """Ranks starting at 1, ties replaced by their average rank."""
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    # Start index of each run of equal values
    starts = np.flatnonzero(np.r_[True, sorted_values[1:] != sorted_values[:-1]])
    ends = np.r_[starts[1:], len(values)]
    average_ranks = (starts + ends + 1) / 2  # mean of ranks start+1 .. end
    ranks = np.empty(len(values))
    ranks[order] = np.repeat(average_ranks, ends - starts)
    return ranks


# ---------------------------------------------------------------------------
# Categorical
# ---------------------------------------------------------------------------


@categorical("accuracy", "Accuracy")
def accuracy(cm: np.ndarray, labels: list[str]) -> float:
    """Share of exact matches."""
    total = cm.sum()
    if total == 0:
        raise Undefined("No rows")
    return float(np.trace(cm) / total)


@categorical("f1_macro", "Macro F1")
def f1_macro(cm: np.ndarray, labels: list[str]) -> float:
    """Unweighted mean of per-class F1, over classes seen in truth or prediction."""
    true_positives = np.diag(cm)
    support = cm.sum(axis=1) + cm.sum(axis=0)  # 2·TP + FP + FN
    present = support > 0
    if not present.any():
        raise Undefined("No rows")
    return float(np.mean(2 * true_positives[present] / support[present]))


@categorical("cohen_kappa", "Cohen κ")
def cohen_kappa(cm: np.ndarray, labels: list[str]) -> float:
    """Agreement corrected for chance, all disagreements weighted equally."""
    n_classes = len(cm)
    weights = 1 - np.eye(n_classes)
    return _weighted_kappa(cm, weights)


@categorical("qwk", "Quadratic weighted κ")
def quadratic_weighted_kappa(cm: np.ndarray, labels: list[str]) -> float:
    """Kappa where a disagreement costs the squared distance between labels.
    Requires numeric (ordinal) labels."""
    values = _numeric_labels(labels)
    if values is None:
        raise Undefined("Requires numeric (ordinal) labels")
    # Distances on label positions, as in scikit-learn's cohen_kappa_score
    positions = np.arange(len(values))
    weights = (positions[:, None] - positions[None, :]) ** 2
    return _weighted_kappa(cm, weights.astype(float))


def _weighted_kappa(cm: np.ndarray, weights: np.ndarray) -> float:
    total = cm.sum()
    if total == 0:
        raise Undefined("No rows")
    expected = np.outer(cm.sum(axis=1), cm.sum(axis=0)) / total
    expected_disagreement = np.sum(weights * expected)
    if expected_disagreement == 0:
        raise Undefined("A single class: kappa is undefined")
    return float(1 - np.sum(weights * cm) / expected_disagreement)


def _numeric_labels(labels: list[str]) -> list[float] | None:
    try:
        return [float(label) for label in labels]
    except ValueError:
        return None


def sort_labels(labels: set[str]) -> list[str]:
    """Numeric order when every label is a number, lexical order otherwise."""
    if _numeric_labels(list(labels)) is not None:
        return sorted(labels, key=float)
    return sorted(labels)
