import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlmodel import select

import async_jobs
import config
import event_bus
from tables import Dataset, Experiment, ExperimentExecution
from tests.conftest import TEST_WORKSPACE_ID, scoped

OTHER_WORKSPACE_ID = 2


@pytest.fixture(autouse=True)
def scheduler(engine, monkeypatch):
    """A scheduler with room for 3 runs, 2 per workspace, whose runs wait on a gate."""
    monkeypatch.setattr(async_jobs, "engine", engine)
    monkeypatch.setattr(config, "MAX_CONCURRENT_EXPERIMENTS", 3)
    monkeypatch.setattr(config, "MAX_CONCURRENT_EXPERIMENTS_PER_WORKSPACE", 2)
    for state in (async_jobs._queue, async_jobs._running_tasks, async_jobs._workspace_of_task):
        state.clear()

    scheduler = type("Scheduler", (), {})()
    scheduler.ran = []
    scheduler.gates = {}

    async def run(experiment_id):
        scheduler.ran.append(experiment_id)
        gate = scheduler.gates.setdefault(experiment_id, asyncio.Event())
        await gate.wait()

    scheduler.finish = lambda experiment_id: scheduler.gates.setdefault(
        experiment_id, asyncio.Event()
    ).set()
    monkeypatch.setattr(async_jobs, "run_experiment_async", run)
    yield scheduler
    for state in (async_jobs._queue, async_jobs._running_tasks, async_jobs._workspace_of_task):
        state.clear()


@pytest.fixture
def make(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO workspace (slug, name, created_at) "
                "VALUES ('other', 'Other', now())"
            )
        )

    def make(workspace_id=TEST_WORKSPACE_ID, **fields) -> int:
        with scoped(engine, workspace_id) as s:
            dataset = Dataset(name="d", file_path="d.csv")
            s.add(dataset)
            s.flush()
            experiment = Experiment(name="e", dataset_id=dataset.id, **fields)
            s.add(experiment)
            s.commit()
            return experiment.id

    return make


def status_of(engine, experiment_id) -> str:
    with scoped(engine) as s:
        return s.get(Experiment, experiment_id).status


async def settle():
    for _ in range(3):
        await asyncio.sleep(0)


def run(scenario):
    async def main():
        try:
            await scenario
        finally:
            for task in list(async_jobs._running_tasks.values()):
                task.cancel()
            await settle()

    asyncio.run(main())


def test_a_workspace_over_its_limit_queues_the_next_run(scheduler, make, engine):
    ids = [make() for _ in range(3)]

    async def scenario():
        with event_bus.subscribe() as events:
            outcomes = [async_jobs.start_experiment(i, TEST_WORKSPACE_ID) for i in ids]
            await settle()

            assert outcomes == ["started", "started", "queued"]
            assert scheduler.ran == ids[:2]
            assert status_of(engine, ids[2]) == "queued"
            published = events.get_nowait()
            assert published.state.status == "queued"
            assert published.state.experiment_id == ids[2]
            assert published.workspace_id == TEST_WORKSPACE_ID

            scheduler.finish(ids[0])
            await settle()
            assert scheduler.ran == ids
            assert async_jobs._queue == []

        for experiment_id in ids[1:]:
            scheduler.finish(experiment_id)
        await settle()

    run(scenario())


def test_the_instance_limit_applies_across_workspaces(scheduler, make):
    first = [make() for _ in range(2)]
    second = [make(OTHER_WORKSPACE_ID) for _ in range(2)]

    async def scenario():
        for i in first:
            async_jobs.start_experiment(i, TEST_WORKSPACE_ID)
        outcomes = [
            async_jobs.start_experiment(i, OTHER_WORKSPACE_ID) for i in second
        ]
        await settle()

        assert outcomes == ["started", "queued"]
        assert len(scheduler.ran) == 3

    run(scenario())


def test_a_full_workspace_does_not_hold_back_another(scheduler, make):
    mine = [make() for _ in range(3)]
    theirs = make(OTHER_WORKSPACE_ID)

    async def scenario():
        for i in mine:
            async_jobs.start_experiment(i, TEST_WORKSPACE_ID)
        # The instance has a slot left, but not for my workspace
        assert async_jobs.start_experiment(theirs, OTHER_WORKSPACE_ID) == "started"
        await settle()

        assert scheduler.ran == [mine[0], mine[1], theirs]
        assert async_jobs._queue == [(mine[2], TEST_WORKSPACE_ID)]

    run(scenario())


def test_a_waiting_run_skipped_for_its_workspace_starts_when_the_instance_frees_up(
    scheduler, make
):
    mine = [make() for _ in range(2)]
    theirs = [make(OTHER_WORKSPACE_ID) for _ in range(2)]

    async def scenario():
        for i in mine:
            async_jobs.start_experiment(i, TEST_WORKSPACE_ID)
        async_jobs.start_experiment(theirs[0], OTHER_WORKSPACE_ID)
        async_jobs.start_experiment(theirs[1], OTHER_WORKSPACE_ID)
        await settle()
        assert theirs[1] not in scheduler.ran

        scheduler.finish(mine[0])
        await settle()

        assert theirs[1] in scheduler.ran

    run(scenario())


def test_the_oldest_waiting_run_of_a_workspace_goes_first(scheduler, make):
    ids = [make() for _ in range(4)]

    async def scenario():
        for i in ids:
            async_jobs.start_experiment(i, TEST_WORKSPACE_ID)
        scheduler.finish(ids[0])
        await settle()
        assert scheduler.ran == [ids[0], ids[1], ids[2]]
        assert async_jobs._queue == [(ids[3], TEST_WORKSPACE_ID)]

    run(scenario())


def test_cancelling_a_queued_run_removes_it_without_running_it(scheduler, make, engine):
    ids = [make() for _ in range(3)]

    async def scenario():
        for i in ids:
            async_jobs.start_experiment(i, TEST_WORKSPACE_ID)

        assert async_jobs.cancel_experiment(ids[2]) is True

        assert async_jobs._queue == []
        assert status_of(engine, ids[2]) == "cancelled"
        scheduler.finish(ids[0])
        await settle()
        assert ids[2] not in scheduler.ran

    run(scenario())


def test_cancelling_an_unknown_experiment_does_nothing(scheduler):
    async def scenario():
        assert async_jobs.cancel_experiment(999) is False

    run(scenario())


def test_starting_a_queued_run_again_keeps_a_single_place(scheduler, make):
    ids = [make() for _ in range(3)]

    async def scenario():
        for i in ids:
            async_jobs.start_experiment(i, TEST_WORKSPACE_ID)
        assert async_jobs.start_experiment(ids[2], TEST_WORKSPACE_ID) == "queued"
        assert async_jobs._queue == [(ids[2], TEST_WORKSPACE_ID)]

    run(scenario())


def test_restarting_a_running_experiment_keeps_its_slot(scheduler, make):
    ids = [make() for _ in range(2)]

    async def scenario():
        for i in ids:
            async_jobs.start_experiment(i, TEST_WORKSPACE_ID)
        await settle()

        assert async_jobs.start_experiment(ids[0], TEST_WORKSPACE_ID) == "started"
        await settle()

        assert scheduler.ran.count(ids[0]) == 2
        assert len(async_jobs._running_tasks) == 2

    run(scenario())


def test_a_finished_run_frees_its_slot(scheduler, make):
    first, second, third = (make() for _ in range(3))

    async def scenario():
        async_jobs.start_experiment(first, TEST_WORKSPACE_ID)
        async_jobs.start_experiment(second, TEST_WORKSPACE_ID)
        scheduler.finish(first)
        await settle()

        assert async_jobs.start_experiment(third, TEST_WORKSPACE_ID) == "started"

    run(scenario())


def test_a_restart_leaves_no_run_marked_as_going(engine, make):
    states = {
        "running": "interrupted",
        "queued": "interrupted",
        "completed": "completed",
        "pending": "pending",
        "failed": "failed",
    }
    experiments = {status: make(status=status) for status in states}
    other = make(OTHER_WORKSPACE_ID, status="running")
    with scoped(engine) as s:
        s.add(
            ExperimentExecution(
                experiment_id=experiments["running"], dataset_snapshot="{}"
            )
        )
        s.add(
            ExperimentExecution(
                experiment_id=experiments["completed"],
                dataset_snapshot="{}",
                status="completed",
            )
        )
        s.commit()

    assert async_jobs.reap_interrupted_runs() == 3

    for status, expected in states.items():
        assert status_of(engine, experiments[status]) == expected
    with scoped(engine, OTHER_WORKSPACE_ID) as s:
        assert s.get(Experiment, other).status == "interrupted"
    with scoped(engine) as s:
        by_experiment = {
            e.experiment_id: e for e in s.exec(select(ExperimentExecution)).all()
        }
    cut_short = by_experiment[experiments["running"]]
    assert cut_short.status == "interrupted"
    assert cut_short.completed_at is not None
    assert cut_short.completed_at.replace(tzinfo=UTC) <= datetime.now(UTC)
    assert by_experiment[experiments["completed"]].status == "completed"
    assert async_jobs.reap_interrupted_runs() == 0
