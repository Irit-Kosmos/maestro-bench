import math

import pytest

from analysis.extract import (
    ExclusionReason,
    extract_pairs,
    get_path,
    to_category,
    to_numeric,
)
from tests.analysis.conftest import make_row


@pytest.mark.parametrize(
    ("obj", "path", "expected"),
    [
        ({"score": 4}, "score", 4),
        ({"evaluation": {"score": 3}}, "evaluation.score", 3),
        ({"labels": ["a", "b"]}, "labels.1", "b"),
        ("4", "", "4"),
    ],
)
def test_get_path(obj, path, expected):
    assert get_path(obj, path) == expected


@pytest.mark.parametrize("path", ["missing", "labels.5", "labels.x", "score.deep"])
def test_get_path_missing(path):
    from core.json_output import MISSING

    assert get_path({"score": 4, "labels": ["a"]}, path) is MISSING


@pytest.mark.parametrize(
    ("value", "expected"),
    [(4, 4.0), (4.5, 4.5), ("4", 4.0), (" 3.5 ", 3.5)],
)
def test_to_numeric_accepts(value, expected):
    assert to_numeric(value) == expected


@pytest.mark.parametrize(
    "value", [None, True, "four", "", [4], {"v": 4}, math.nan, "inf"]
)
def test_to_numeric_rejects(value):
    assert to_numeric(value) is None


def test_to_category_canonical_numbers():
    assert to_category(4) == to_category(4.0) == to_category(" 4 ") == "4"
    assert to_category("4.50") == to_category(4.5) == "4.5"


def test_to_category_case():
    assert to_category(" Positive ") == "Positive"
    assert to_category("Positive", ignore_case=True) == "positive"
    assert to_category(True) == "true"


@pytest.mark.parametrize("value", [None, "", "  ", [1], {"a": 1}, math.nan])
def test_to_category_rejects(value):
    assert to_category(value) is None


def test_extract_pairs_exclusion_reasons(not_reached):
    rows = [
        make_row(1, truth=3, output={"score": 4}),
        make_row(2, truth=3, output={"score": "4"}),
        make_row(3, truth=3, output=None, error="timeout"),
        make_row(4, truth=3, output=not_reached),
        make_row(5, truth=3, output="not json at all"),
        make_row(6, truth=3, output={"feedback": "no score"}),
        make_row(7, truth=3, output={"score": "four"}),
        make_row(8, truth=None, output={"score": 4}),
        make_row(9, truth=math.nan, output={"score": 4}),
    ]
    extraction = extract_pairs(rows, "Grader", "score", "score", "numeric")

    assert extraction.predictions == [4.0, 4.0]
    assert extraction.truths == [3.0, 3.0]
    assert extraction.row_indices == [1, 2]
    assert [(e.row_index, e.reason) for e in extraction.excluded] == [
        (3, ExclusionReason.AGENT_ERROR),
        (4, ExclusionReason.AGENT_ERROR),
        (5, ExclusionReason.UNPARSED_OUTPUT),
        (6, ExclusionReason.PATH_MISSING),
        (7, ExclusionReason.INVALID_VALUE),
        (8, ExclusionReason.TRUTH_MISSING),
        (9, ExclusionReason.TRUTH_MISSING),
    ]
    assert extraction.n_total == 9


def test_extract_pairs_selects_agent():
    row = make_row(1, truth=2, output={"score": 1}, agent="First")
    row["agents"].append({"name": "Second", "output": {"score": 5}, "error": None})

    extraction = extract_pairs([row], "Second", "score", "score", "numeric")

    assert extraction.predictions == [5.0]


def test_extract_pairs_whole_text_output():
    rows = [make_row(1, truth="Positive", output=" positive ")]

    strict = extract_pairs(rows, "Grader", "", "score", "categorical")
    relaxed = extract_pairs(
        rows, "Grader", "", "score", "categorical", ignore_case=True
    )

    assert strict.predictions == ["positive"] and strict.truths == ["Positive"]
    assert relaxed.predictions == relaxed.truths == ["positive"]


def test_excluded_rows_keep_dataset_row_id():
    rows = [make_row(1, truth=None, output={"score": 1}, dataset_row_id=41)]

    extraction = extract_pairs(rows, "Grader", "score", "score", "numeric")

    assert extraction.excluded[0].dataset_row_id == 41


def test_extract_pairs_repairs_unparsed_outputs():
    rows = [
        make_row(1, truth=3, output='```json\n{"score": 4}\n```'),
        make_row(2, truth=3, output='{\n  "score": 2,\n  "reasoning": "x",\n}'),
        make_row(3, truth=3, output='{"reasoning": "bad \\0 escape", "score": 1}'),
    ]
    extraction = extract_pairs(rows, "Grader", "score", "score", "numeric")

    assert extraction.predictions == [4.0, 2.0]
    assert [e.reason for e in extraction.excluded] == [ExclusionReason.UNPARSED_OUTPUT]
