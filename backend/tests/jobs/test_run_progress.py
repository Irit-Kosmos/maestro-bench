import pytest

import event_bus
from async_jobs import _RunProgress
from tables import Dataset, Experiment, ExperimentExecution


@pytest.fixture
def execution(session):
    dataset = Dataset(name="answers", file_path="answers.csv")
    session.add(dataset)
    session.flush()
    experiment = Experiment(name="Run", dataset_id=dataset.id)
    session.add(experiment)
    session.flush()
    execution = ExperimentExecution(experiment_id=experiment.id, dataset_snapshot="{}")
    session.add(execution)
    session.commit()
    return execution


def test_rows_are_counted_in_the_database_and_published(session, execution):
    progress = _RunProgress(session, execution, batch_id=5, workspace_id=1)

    with event_bus.subscribe() as queue:
        progress.start(3)
        progress.row_done(failed=False)
        progress.row_done(failed=True)

        events = [queue.get_nowait() for _ in range(3)]

    assert {event.name for event in events} == {"progress"}
    assert [
        (e.state.rows_total, e.state.rows_done, e.state.rows_failed) for e in events
    ] == [(3, 0, 0), (3, 1, 0), (3, 2, 1)]
    assert {e.state.batch_id for e in events} == {5}

    session.refresh(execution)
    assert (execution.rows_total, execution.rows_done, execution.rows_failed) == (
        3,
        2,
        1,
    )


def test_published_events_are_not_altered_by_later_rows(session, execution):
    progress = _RunProgress(session, execution, batch_id=None, workspace_id=1)

    with event_bus.subscribe() as queue:
        progress.start(2)
        progress.row_done(failed=False)

        assert [queue.get_nowait().state.rows_done for _ in range(2)] == [0, 1]


def test_announce_publishes_a_status_event(session, execution):
    progress = _RunProgress(session, execution, batch_id=None, workspace_id=1)

    with event_bus.subscribe() as queue:
        progress.announce("completed")

        event = queue.get_nowait()

    assert event.name == "status"
    assert event.state.status == "completed"
    assert event.state.execution_id == execution.id
