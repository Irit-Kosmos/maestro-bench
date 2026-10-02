from execution_stats import latest_figures
from tables import ExperimentExecution


def _execution(status: str) -> ExperimentExecution:
    return ExperimentExecution(experiment_id=1, dataset_snapshot="{}", status=status)


def test_lists_the_status_of_every_execution_newest_first():
    figures = latest_figures([_execution("completed"), _execution("failed"), _execution("cancelled")])

    assert figures["execution_count"] == 3
    assert figures["execution_statuses"] == ["completed", "failed", "cancelled"]


def test_has_no_status_without_execution():
    figures = latest_figures([])

    assert figures["execution_count"] == 0
    assert figures["execution_statuses"] == []
