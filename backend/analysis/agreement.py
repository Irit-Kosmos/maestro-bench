# MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
# Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
# Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Agreement between several columns that rate the same rows (two annotators,
a human and an average...).

Pairwise, every pair of columns is compared on the rows both rated, reusing
the metrics of ``analysis.metrics``. Overall, Krippendorff's alpha summarises
all the columns at once and copes with missing ratings.

Blank cells and values that do not fit the value type are left out, never
defaulted, and counted so the coverage can be shown with the numbers.
"""

from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

import numpy as np

from analysis.extract import ValueType, to_category, to_numeric
from analysis.metrics import METRICS, Undefined, sort_labels

# Metrics of a pair, in display order. Every one is symmetric: swapping the two
# columns gives the same value.
PAIR_METRICS: dict[ValueType, tuple[str, ...]] = {
    "numeric": ("accuracy", "mae", "pearson", "spearman", "qwk", "cohen_kappa"),
    "categorical": ("accuracy", "cohen_kappa"),
}

# Under this many rated rows an agreement estimate is too noisy to rely on
SMALL_SAMPLE_ROWS = 30

# Here ``accuracy`` and ``mae`` do not compare a model with a truth
_RENAMED = {
    "accuracy": ("Exact agreement", "Share of rows where both columns give the same value."),
    "mae": ("Mean abs. difference", "Average gap between the two columns."),
}


@dataclass(frozen=True)
class PairMetricInfo:
    key: str
    label: str
    description: str


def pair_metric_infos(value_type: ValueType) -> list[PairMetricInfo]:
    """The metrics computed for each pair, as the reader should name them."""
    return [
        PairMetricInfo(key, *_RENAMED.get(key, (METRICS[key].label, METRICS[key].description)))
        for key in PAIR_METRICS[value_type]
    ]


@dataclass
class AgreementValue:
    value: float | None
    undefined_reason: str | None = None


@dataclass
class ColumnSummary:
    column: str
    # Rows with a usable value; the rest of the rows are blank or invalid
    n: int
    n_missing: int
    mean: float | None = None


@dataclass
class PairAgreement:
    a: str
    b: str
    # Rows rated by both columns
    n: int
    metrics: dict[str, AgreementValue]


@dataclass
class OverallAgreement:
    # Rows rated by at least two columns: the only ones that can agree or not
    n_items: int
    # Share of those rows where every rating is the same
    unanimous: float | None
    alpha: AgreementValue


@dataclass
class AgreementResult:
    value_type: ValueType
    n_rows: int
    columns: list[ColumnSummary]
    pairs: list[PairAgreement]
    overall: OverallAgreement
    warnings: list[str] = field(default_factory=list)


def detect_value_type(columns: dict[str, list[Any]]) -> ValueType:
    """Numeric when every non-blank value is a number, categorical otherwise."""
    seen = False
    for values in columns.values():
        for value in values:
            if _is_blank(value):
                continue
            seen = True
            if to_numeric(value) is None:
                return "categorical"
    return "numeric" if seen else "categorical"


def compute_agreement(
    columns: dict[str, list[Any]], value_type: ValueType | None = None
) -> AgreementResult:
    """Agreement of ``columns``: name -> one raw value per row, rows aligned."""
    if len(columns) < 2:
        raise ValueError("Select at least two columns")
    lengths = {len(values) for values in columns.values()}
    if len(lengths) != 1:
        raise ValueError("The columns do not have the same number of rows")
    n_rows = lengths.pop()
    value_type = value_type or detect_value_type(columns)

    convert = to_numeric if value_type == "numeric" else to_category
    converted = {
        name: [None if _is_blank(v) else convert(v) for v in values]
        for name, values in columns.items()
    }

    # One label scale for every pair: codes mean the same in each comparison
    labels = sort_labels(
        {
            _label(v, value_type)
            for values in converted.values()
            for v in values
            if v is not None
        }
    )
    code = {label: i for i, label in enumerate(labels)}
    codes = {
        name: np.array(
            [-1 if v is None else code[_label(v, value_type)] for v in values],
            dtype=int,
        )
        for name, values in converted.items()
    }

    summaries = [
        _summarise(name, converted[name], value_type, n_rows) for name in converted
    ]
    pairs = [
        _pair(a, b, codes, labels, value_type) for a, b in combinations(converted, 2)
    ]
    result = AgreementResult(
        value_type=value_type,
        n_rows=n_rows,
        columns=summaries,
        pairs=pairs,
        overall=_overall(codes, labels, value_type),
    )
    result.warnings = _warnings(result)
    return result


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and value != value:  # NaN
        return True
    return isinstance(value, str) and not value.strip()


def _label(value: Any, value_type: ValueType) -> str:
    """Canonical text of a value, so 4, 4.0 and "4" are the same label."""
    return to_category(value) if value_type == "numeric" else value


def _summarise(
    name: str, values: list[Any], value_type: ValueType, n_rows: int
) -> ColumnSummary:
    valid = [v for v in values if v is not None]
    return ColumnSummary(
        column=name,
        n=len(valid),
        n_missing=n_rows - len(valid),
        mean=float(np.mean(valid)) if valid and value_type == "numeric" else None,
    )


def _value(fn, *args) -> AgreementValue:
    try:
        return AgreementValue(fn(*args))
    except Undefined as e:
        return AgreementValue(None, str(e))


def _pair(
    a: str,
    b: str,
    codes: dict[str, np.ndarray],
    labels: list[str],
    value_type: ValueType,
) -> PairAgreement:
    both = (codes[a] >= 0) & (codes[b] >= 0)
    n = int(both.sum())
    if n == 0:
        reason = "No row is rated by both columns"
        return PairAgreement(
            a, b, 0, {k: AgreementValue(None, reason) for k in PAIR_METRICS[value_type]}
        )

    k = len(labels)
    cm = np.bincount(codes[a][both] * k + codes[b][both], minlength=k * k).reshape(k, k)
    if value_type == "numeric":
        values = np.array([float(label) for label in labels])
        x, y = values[codes[a][both]], values[codes[b][both]]

    metrics: dict[str, AgreementValue] = {}
    for key in PAIR_METRICS[value_type]:
        metric = METRICS[key]
        if metric.kind == "numeric":
            metrics[key] = _value(metric.fn, x, y)
        else:
            metrics[key] = _value(metric.fn, cm, labels)
    return PairAgreement(a, b, n, metrics)


def _overall(
    codes: dict[str, np.ndarray], labels: list[str], value_type: ValueType
) -> OverallAgreement:
    matrix = np.stack(list(codes.values()), axis=1)
    rated = (matrix >= 0).sum(axis=1)
    items = rated >= 2

    distance = _distance(labels, value_type)
    alpha = _value(krippendorff_alpha, matrix, distance)

    n_items = int(items.sum())
    unanimous = None
    if n_items:
        highest = matrix.max(axis=1)
        same = np.all((matrix < 0) | (matrix == highest[:, None]), axis=1)
        unanimous = float(same[items].mean())
    return OverallAgreement(n_items=n_items, unanimous=unanimous, alpha=alpha)


def _distance(labels: list[str], value_type: ValueType) -> np.ndarray:
    """Cost of mistaking one label for another: squared gap, or 0/1 for classes."""
    if value_type == "numeric":
        values = np.array([float(label) for label in labels])
        return (values[:, None] - values[None, :]) ** 2
    return 1.0 - np.eye(len(labels))


def krippendorff_alpha(matrix: np.ndarray, distance: np.ndarray) -> float:
    """
    Krippendorff's alpha: 1 minus observed over expected disagreement.

    ``matrix`` holds one label code per cell (rows = units, columns = raters,
    -1 = no rating); ``distance[c, k]`` is the cost of rating c where k was
    given. Units with fewer than two ratings cannot disagree and are skipped.
    """
    k = len(distance)
    counts = np.stack([(matrix == c).sum(axis=1) for c in range(k)], axis=1)
    totals = counts.sum(axis=1)
    pairable = totals >= 2
    if not pairable.any():
        raise Undefined("No row is rated by at least two columns")

    counts = counts[pairable].astype(float)
    weights = 1.0 / (totals[pairable] - 1)
    # Ordered pairs of ratings within a unit, each unit weighing its pairs
    coincidence = (counts * weights[:, None]).T @ counts
    coincidence -= np.diag((counts * weights[:, None]).sum(axis=0))

    n = coincidence.sum()
    marginals = coincidence.sum(axis=1)
    expected = np.sum(np.outer(marginals, marginals) * distance) / (n - 1)
    if expected == 0:
        raise Undefined("A single value is used: alpha is undefined")
    return float(1 - np.sum(coincidence * distance) / expected)


def _warnings(result: AgreementResult) -> list[str]:
    warnings = []
    if result.overall.n_items < SMALL_SAMPLE_ROWS:
        warnings.append(
            f"Only {result.overall.n_items} rows are rated by two columns or more: "
            "the agreement is not reliable"
        )
    return warnings
