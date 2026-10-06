"""Reference values from Krippendorff's worked example and the definitions."""

from itertools import permutations

import numpy as np
import pytest

from analysis.agreement import compute_agreement, detect_value_type

# Krippendorff (2011), "Computing Krippendorff's Alpha-Reliability":
# four observers, twelve units, some ratings missing
EXAMPLE = {
    "A": [1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None],
    "B": [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, 3],
    "C": [None, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, None],
    "D": [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, None],
}


def _brute_force_alpha(columns, squared_gap: bool) -> float:
    """Definition of alpha on every pair of ratings, with no shortcut."""
    units = [
        [column[i] for column in columns.values() if column[i] is not None]
        for i in range(len(next(iter(columns.values()))))
    ]
    units = [u for u in units if len(u) >= 2]
    gap = (lambda c, k: (c - k) ** 2) if squared_gap else (lambda c, k: float(c != k))

    observed = sum(
        sum(gap(c, k) for c, k in permutations(u, 2)) / (len(u) - 1) for u in units
    )
    values = [v for u in units for v in u]
    n = len(values)
    expected = sum(gap(c, k) for c, k in permutations(values, 2)) / (n - 1)
    return 1 - observed / expected


def test_krippendorff_example():
    nominal = compute_agreement(EXAMPLE, "categorical").overall.alpha.value
    interval = compute_agreement(EXAMPLE, "numeric").overall.alpha.value
    assert nominal == pytest.approx(0.743, abs=1e-3)
    assert interval == pytest.approx(0.849, abs=1e-3)


@pytest.mark.parametrize(("value_type", "squared"), [("categorical", False), ("numeric", True)])
def test_alpha_matches_the_definition(value_type, squared):
    rng = np.random.default_rng(3)
    columns = {
        name: [None if rng.random() < 0.2 else int(rng.integers(0, 6)) for _ in range(40)]
        for name in "XYZ"
    }
    alpha = compute_agreement(columns, value_type).overall.alpha.value
    assert alpha == pytest.approx(_brute_force_alpha(columns, squared))


def test_perfect_and_partial_agreement():
    perfect = compute_agreement({"a": [1, 2, 3, 4], "b": [1, 2, 3, 4]})
    assert perfect.overall.alpha.value == pytest.approx(1)
    assert perfect.overall.unanimous == 1
    assert perfect.pairs[0].metrics["accuracy"].value == 1
    assert perfect.pairs[0].metrics["qwk"].value == pytest.approx(1)

    off_by_one = compute_agreement({"a": [1, 2, 3, 4], "b": [2, 2, 3, 3]})
    pair = off_by_one.pairs[0]
    assert pair.metrics["accuracy"].value == 0.5
    assert pair.metrics["mae"].value == 0.5
    assert off_by_one.overall.unanimous == 0.5


def test_pair_metrics_match_reference():
    a = [1, 2, 2, 3, 5, 4, 3, 2]
    b = [1, 3, 2, 4, 4, 5, 3, 1]
    metrics = compute_agreement({"a": a, "b": b}).pairs[0].metrics
    assert metrics["pearson"].value == pytest.approx(np.corrcoef(a, b)[0, 1])
    assert metrics["accuracy"].value == pytest.approx(3 / 8)
    assert metrics["mae"].value == pytest.approx(5 / 8)
    # 1 - observed / chance-expected disagreement, worked out from the definition
    assert metrics["qwk"].value == pytest.approx(0.8113207547169812)
    assert metrics["cohen_kappa"].value == pytest.approx(0.23076923076923073)


def test_pairs_only_use_rows_rated_by_both():
    result = compute_agreement(
        {"a": [1, 2, 3, ""], "b": [1, "", 3, 4], "c": [1, 2, 2, 4]}
    )
    sizes = {(p.a, p.b): p.n for p in result.pairs}
    assert sizes == {("a", "b"): 2, ("a", "c"): 3, ("b", "c"): 3}
    assert [c.n_missing for c in result.columns] == [1, 1, 0]
    assert result.columns[0].mean == pytest.approx(2)


def test_categorical_columns():
    result = compute_agreement(
        {"a": ["yes", "no", "yes", "no"], "b": ["yes", "no", "no", "no"]}
    )
    assert result.value_type == "categorical"
    assert set(result.pairs[0].metrics) == {"accuracy", "cohen_kappa"}
    assert result.pairs[0].metrics["accuracy"].value == 0.75
    assert result.columns[0].mean is None


def test_value_type_is_detected():
    assert detect_value_type({"a": ["1", "2.5", ""], "b": ["3"]}) == "numeric"
    assert detect_value_type({"a": ["1", "two"]}) == "categorical"
    assert detect_value_type({"a": ["", " "]}) == "categorical"


def test_numbers_written_differently_are_the_same_label():
    result = compute_agreement({"a": ["4", "3.0", "5"], "b": [4.0, "3", "5.0"]}, "categorical")
    assert result.pairs[0].metrics["accuracy"].value == 1


def test_undefined_values_say_why():
    constant = compute_agreement({"a": [3, 3, 3], "b": [3, 3, 3]})
    assert constant.overall.alpha.value is None
    assert "single value" in constant.overall.alpha.undefined_reason
    assert constant.pairs[0].metrics["pearson"].value is None

    disjoint = compute_agreement({"a": [1, 2, "", ""], "b": ["", "", 3, 4]})
    assert disjoint.pairs[0].n == 0
    assert disjoint.pairs[0].metrics["accuracy"].undefined_reason
    assert disjoint.overall.n_items == 0
    assert disjoint.overall.unanimous is None
    assert disjoint.overall.alpha.value is None


def test_small_samples_are_flagged():
    assert compute_agreement({"a": [1, 2], "b": [1, 2]}).warnings
    big = list(range(40))
    assert not compute_agreement({"a": big, "b": big}).warnings


def test_input_is_checked():
    with pytest.raises(ValueError, match="at least two"):
        compute_agreement({"a": [1, 2]})
    with pytest.raises(ValueError, match="same number"):
        compute_agreement({"a": [1, 2], "b": [1]})
