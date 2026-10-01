"""Reference values computed with scipy 1.x and scikit-learn 1.x."""

import numpy as np
import pytest

from analysis.metrics import METRICS, Undefined, sort_labels


def _numeric(key, pred, truth):
    return METRICS[key].fn(np.array(pred, float), np.array(truth, float))


def _categorical(key, truth, pred):
    labels = sort_labels(set(truth) | set(pred))
    code = {label: i for i, label in enumerate(labels)}
    cm = np.zeros((len(labels), len(labels)), dtype=int)
    for t, p in zip(truth, pred, strict=True):
        cm[code[t], code[p]] += 1
    return METRICS[key].fn(cm, labels)


def test_error_metrics():
    pred, truth = [1, 2, 3, 5], [1, 2, 5, 4]
    assert _numeric("rmse", pred, truth) == pytest.approx(np.sqrt(5 / 4))
    assert _numeric("mae", pred, truth) == pytest.approx(3 / 4)
    assert _numeric("bias", pred, truth) == pytest.approx(-1 / 4)


def test_correlations_with_ties():
    x, y = [1, 2, 2, 3, 5, 4], [1, 3, 2, 4, 4, 6]
    assert _numeric("pearson", x, y) == pytest.approx(0.801753930173401)
    assert _numeric("spearman", x, y) == pytest.approx(0.8823529411764706)


@pytest.mark.parametrize("key", ["pearson", "spearman"])
def test_correlation_undefined(key):
    with pytest.raises(Undefined):
        _numeric(key, [3, 3, 3], [1, 2, 3])
    with pytest.raises(Undefined):
        _numeric(key, [1], [1])


TRUTH = ["0", "1", "2", "2", "3", "1", "0", "3"]
PRED = ["0", "2", "2", "1", "3", "1", "1", "3"]


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("accuracy", 0.625),
        ("f1_macro", 0.6416666666666666),
        ("cohen_kappa", 0.5),
        ("qwk", 0.8333333333333334),
    ],
)
def test_categorical_metrics(key, expected):
    assert _categorical(key, TRUTH, PRED) == pytest.approx(expected)


def test_f1_macro_counts_classes_seen_only_in_truth():
    # sklearn f1_score(average="macro", zero_division=0)
    value = _categorical("f1_macro", ["a", "b", "a", "c"], ["a", "a", "a", "b"])
    assert value == pytest.approx(0.26666666666666666)


def test_kappa_single_class_undefined():
    with pytest.raises(Undefined):
        _categorical("cohen_kappa", ["a", "a"], ["a", "a"])


def test_qwk_requires_numeric_labels():
    with pytest.raises(Undefined, match="numeric"):
        _categorical("qwk", ["low", "high"], ["low", "low"])


def test_sort_labels():
    assert sort_labels({"10", "2", "1.5"}) == ["1.5", "2", "10"]
    assert sort_labels({"b", "a", "10"}) == ["10", "a", "b"]


def test_registry_kinds():
    numeric = {k for k, m in METRICS.items() if m.kind == "numeric"}
    categorical = {k for k, m in METRICS.items() if m.kind == "categorical"}
    assert numeric == {"rmse", "mae", "bias", "pearson", "spearman"}
    assert categorical == {"accuracy", "f1_macro", "cohen_kappa", "qwk"}
    assert all(m.description for m in METRICS.values())
