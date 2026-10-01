import numpy as np
import pytest

from analysis import AnalysisConfig, RunInput, compute_analysis, validate_config
from tests.analysis.conftest import make_row, scored_rows

PAIRS = [(4, 3.5), (5, 5), (2, 3), (0, 0.5), (3, 3), (5, 4.5), (1, 2), (4, 4)]


def numeric_config(**overrides) -> AnalysisConfig:
    return AnalysisConfig(
        truth_column="score",
        output_path="score",
        value_type="numeric",
        metrics=["rmse", "mae", "pearson", "spearman", "bias"],
        **overrides,
    )


def test_numeric_run_matches_reference_computation():
    result = compute_analysis(
        numeric_config(), [RunInput("A", "Grader", scored_rows(PAIRS))]
    )
    run = result.runs[0]

    pred = np.array([p for p, _ in PAIRS], float)
    truth = np.array([t for _, t in PAIRS], float)
    assert run.metrics["rmse"].value == pytest.approx(
        np.sqrt(np.mean((pred - truth) ** 2))
    )
    assert run.metrics["pearson"].value == pytest.approx(np.corrcoef(pred, truth)[0, 1])
    assert (run.n_valid, run.n_total, run.coverage) == (8, 8, 1.0)
    assert len(run.points) == 8
    assert run.confusion is None


def test_bootstrap_matches_notebook_procedure():
    """Same resampling as maestro-analysis' bootstrap_ci (seed 0, 1000 draws)."""
    run = compute_analysis(
        numeric_config(), [RunInput("A", "Grader", scored_rows(PAIRS))]
    ).runs[0]

    pred = np.array([p for p, _ in PAIRS], float)
    truth = np.array([t for _, t in PAIRS], float)
    rng = np.random.default_rng(0)
    idx = rng.integers(0, len(pred), (1000, len(pred)))
    boots = [np.mean(np.abs(pred[i] - truth[i])) for i in idx]
    low, high = np.quantile(boots, [0.025, 0.975])

    assert run.metrics["mae"].ci_low == pytest.approx(low)
    assert run.metrics["mae"].ci_high == pytest.approx(high)


def test_bootstrap_is_deterministic_and_seeded():
    runs = [RunInput("A", "Grader", scored_rows(PAIRS))]
    first = compute_analysis(numeric_config(), runs).runs[0].metrics["rmse"]
    again = compute_analysis(numeric_config(), runs).runs[0].metrics["rmse"]
    other = compute_analysis(numeric_config(seed=7), runs).runs[0].metrics["rmse"]

    assert (first.ci_low, first.ci_high) == (again.ci_low, again.ci_high)
    assert (first.ci_low, first.ci_high) != (other.ci_low, other.ci_high)


def test_confidence_level_widens_interval():
    runs = [RunInput("A", "Grader", scored_rows(PAIRS))]
    narrow = compute_analysis(numeric_config(confidence=0.9), runs)
    wide = compute_analysis(numeric_config(confidence=0.99), runs)
    n, w = narrow.runs[0].metrics["mae"], wide.runs[0].metrics["mae"]

    assert w.ci_low <= n.ci_low and w.ci_high >= n.ci_high


def test_undefined_metric_is_reported_not_zero():
    rows = scored_rows([(3, 1), (3, 2), (3, 4)])
    run = compute_analysis(numeric_config(), [RunInput("A", "Grader", rows)]).runs[0]

    pearson = run.metrics["pearson"]
    assert pearson.value is None and pearson.ci_low is None
    assert "Constant" in pearson.undefined_reason
    assert run.metrics["rmse"].value is not None


def test_coverage_and_exclusions():
    rows = scored_rows(PAIRS) + [
        make_row(9, truth=3, output={"other": 1}),
        make_row(10, truth=None, output={"score": 1}),
    ]
    run = compute_analysis(numeric_config(), [RunInput("A", "Grader", rows)]).runs[0]

    assert (run.n_valid, run.n_total) == (8, 10)
    assert run.exclusions == {"path_missing": 1, "truth_missing": 1}
    assert [e.row_index for e in run.excluded_rows] == [9, 10]
    assert any("80%" in w for w in run.warnings)


def test_no_usable_rows():
    rows = [make_row(1, truth=None, output={"score": 1})]
    run = compute_analysis(numeric_config(), [RunInput("A", "Grader", rows)]).runs[0]

    assert run.n_valid == 0
    assert all(m.value is None for m in run.metrics.values())


def test_categorical_run():
    rows = [
        make_row(i, truth=t, output={"label": p})
        for i, (t, p) in enumerate(
            [("pos", "pos"), ("neg", "pos"), ("neg", "neg"), ("pos", "pos")]
        )
    ]
    config = AnalysisConfig(
        truth_column="score",
        output_path="label",
        value_type="categorical",
        metrics=["accuracy", "cohen_kappa"],
        n_boot=50,
    )
    run = compute_analysis(config, [RunInput("A", "Grader", rows)]).runs[0]

    assert run.metrics["accuracy"].value == pytest.approx(0.75)
    assert run.confusion == {"labels": ["neg", "pos"], "matrix": [[1, 1], [0, 2]]}
    assert run.points is None


def test_validate_config():
    with pytest.raises(ValueError, match="Unknown"):
        validate_config(_with(metrics=["nope"]))
    with pytest.raises(ValueError, match="categorical"):
        validate_config(_with(metrics=["accuracy"]))
    with pytest.raises(ValueError, match="at least one"):
        validate_config(_with(metrics=[]))
    with pytest.raises(ValueError, match="Confidence"):
        validate_config(_with(confidence=1.5))


def _with(**overrides) -> AnalysisConfig:
    config = numeric_config()
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def _snapshot(file_path="data.csv", **sampling):
    return {"file_path": file_path, "sampling_config": sampling}


@pytest.mark.parametrize(
    ("snapshots", "expected"),
    [
        ([_snapshot(), _snapshot()], []),
        ([_snapshot(), _snapshot("other.csv")], ["Runs use different datasets"]),
        (
            [
                _snapshot(sampling_type="range", sampling_start_row=1),
                _snapshot(),
            ],
            ["Runs use different samples of the dataset"],
        ),
        (
            [
                _snapshot(sampling_type="random", sampling_size=5),
                _snapshot(sampling_type="random", sampling_size=5),
            ],
            ["Runs use different samples of the dataset"],
        ),
        (
            [
                _snapshot(sampling_type="random", sampling_size=5, sampling_seed=3),
                _snapshot(sampling_type="random", sampling_size=5, sampling_seed=3),
            ],
            [],
        ),
    ],
)
def test_comparison_warnings(snapshots, expected):
    runs = [
        RunInput(f"R{i}", "Grader", scored_rows(PAIRS), dataset=snapshot)
        for i, snapshot in enumerate(snapshots)
    ]
    assert compute_analysis(numeric_config(n_boot=10), runs).warnings == expected
