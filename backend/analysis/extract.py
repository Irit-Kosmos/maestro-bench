"""
Extraction of (prediction, ground truth) pairs from a results file.

A prediction is selected by an agent name and a dotted path into that agent's
JSON output (``score``, ``evaluation.score``, ``labels.0``; an empty path means
the whole output). The ground truth is a column of the dataset row.

Rows that cannot be used are excluded, never defaulted, and the reason is
recorded so coverage can be reported alongside the metrics.
"""

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from core.json_output import MISSING, get_path, parse_json_output

ValueType = Literal["numeric", "categorical"]


class ExclusionReason(StrEnum):
    AGENT_ERROR = "agent_error"  # agent failed or was never reached
    UNPARSED_OUTPUT = "unparsed_output"  # output is not JSON, path cannot apply
    PATH_MISSING = "path_missing"
    INVALID_VALUE = "invalid_value"
    TRUTH_MISSING = "truth_missing"  # empty or not convertible


@dataclass
class ExcludedRow:
    row_index: int | None
    dataset_row_id: int | None
    reason: ExclusionReason


@dataclass
class Extraction:
    """Valid pairs plus the rows that were left out."""

    predictions: list[Any] = field(default_factory=list)
    truths: list[Any] = field(default_factory=list)
    row_indices: list[int | None] = field(default_factory=list)
    excluded: list[ExcludedRow] = field(default_factory=list)

    @property
    def n_valid(self) -> int:
        return len(self.predictions)

    @property
    def n_total(self) -> int:
        return self.n_valid + len(self.excluded)


def to_numeric(value: Any) -> float | None:
    """Accept 4, 4.0 and "4"; reject booleans, NaN, containers and other text."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    return number if math.isfinite(number) else None


def to_category(value: Any, ignore_case: bool = False) -> str | None:
    """
    Normalize a label so that 4, 4.0 and "4 " compare equal.

    Numbers get a canonical form, strings are trimmed (and case-folded on
    request), booleans become "true"/"false". Containers and empty values are
    rejected.
    """
    if value is None or isinstance(value, dict | list):
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        number = float(value)
        if not math.isfinite(number):
            return None
        return _canonical_number(number)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        number = to_numeric(text)
        if number is not None:
            return _canonical_number(number)
        return text.casefold() if ignore_case else text
    return None


def _canonical_number(number: float) -> str:
    return str(int(number)) if number.is_integer() else repr(number)


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return isinstance(value, str) and not value.strip()


def extract_pairs(
    rows: list[dict],
    agent_name: str,
    output_path: str,
    truth_column: str,
    value_type: ValueType,
    ignore_case: bool = False,
) -> Extraction:
    """Build the (prediction, truth) pairs of one execution's result rows."""

    def convert(value: Any) -> Any:
        if value_type == "numeric":
            return to_numeric(value)
        return to_category(value, ignore_case=ignore_case)

    extraction = Extraction()
    for row in rows:
        outcome = _row_pair(row, agent_name, output_path, truth_column, convert)
        if isinstance(outcome, ExclusionReason):
            extraction.excluded.append(
                ExcludedRow(row.get("row_index"), row.get("dataset_row_id"), outcome)
            )
            continue
        prediction, truth = outcome
        extraction.predictions.append(prediction)
        extraction.truths.append(truth)
        extraction.row_indices.append(row.get("row_index"))
    return extraction


def _row_pair(
    row: dict,
    agent_name: str,
    output_path: str,
    truth_column: str,
    convert,
) -> tuple[Any, Any] | ExclusionReason:
    agent = next(
        (a for a in row.get("agents") or [] if a.get("name") == agent_name), None
    )
    if agent is None or agent.get("error"):
        return ExclusionReason.AGENT_ERROR

    # Older results files kept unparsed outputs (fenced, trailing commas)
    output = parse_json_output(agent.get("output"))
    if output_path and isinstance(output, str):
        return ExclusionReason.UNPARSED_OUTPUT

    raw = get_path(output, output_path)
    if raw is MISSING:
        return ExclusionReason.PATH_MISSING

    prediction = convert(raw)
    if prediction is None:
        return ExclusionReason.INVALID_VALUE

    truth_raw = (row.get("input_data") or {}).get(truth_column)
    truth = None if _is_blank(truth_raw) else convert(truth_raw)
    if truth is None:
        return ExclusionReason.TRUTH_MISSING

    return prediction, truth
