from datetime import UTC, datetime, timedelta

import pytest

from api import dashboard
from tables import (
    Agent,
    AgentExecutionSnapshot,
    Batch,
    Dataset,
    Experiment,
    ExperimentAgentConfig,
    ExperimentExecution,
    Model,
    Prompt,
    PromptVersion,
)
from tests.conftest import api_client, scoped


def now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def client(engine):
    return api_client(engine, dashboard)


@pytest.fixture
def world(engine):
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        prompt = Prompt(name="Grader")
        s.add_all([dataset, prompt])
        s.flush()
        version = PromptVersion(prompt_id=prompt.id, version="1")
        models = [Model(name=n, provider="openai") for n in ("m-a", "m-b")]
        s.add_all([version, *models])
        s.flush()
        agent = Agent(name="Grader")
        other_agent = Agent(name="Reviewer")
        s.add_all([agent, other_agent])
        s.commit()
        return {
            "dataset": dataset.id,
            "agent": agent.id,
            "other_agent": other_agent.id,
            "version": version.id,
            "models": [m.id for m in models],
        }


def add_experiment(engine, world, **fields) -> int:
    with scoped(engine) as s:
        experiment = Experiment(name="Run", dataset_id=world["dataset"], **fields)
        s.add(experiment)
        s.commit()
        return experiment.id


def add_execution(engine, experiment_id, models, **fields) -> int:
    """An execution with one agent snapshot per model name."""
    with scoped(engine) as s:
        execution = ExperimentExecution(
            experiment_id=experiment_id, dataset_snapshot="{}", **fields
        )
        s.add(execution)
        s.flush()
        for order, model in enumerate(models):
            s.add(
                AgentExecutionSnapshot(
                    execution_id=execution.id,
                    agent_id=1,
                    agent_name_snapshot=f"agent-{order}",
                    model_name_snapshot=model,
                    model_provider_snapshot="openai",
                    prompt_name_snapshot="Grader",
                    prompt_version_snapshot="1",
                    execution_order=order,
                )
            )
        s.commit()
        return execution.id


def test_empty_database(client):
    body = client.get("/dashboard").json()

    assert body["recent_experiments"] == []
    activity = body["activity"]
    assert activity["range"] == "7d"
    assert activity["current"] == {
        "experiments": 0,
        "completed": 0,
        "failed": 0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "rows_done": 0,
        "rows_failed": 0,
        "experiments_with_failures": 0,
    }
    assert activity["previous"]["experiments"] == 0
    assert activity["active"] == []
    # A week in slices of twelve hours
    assert len(activity["buckets"]) == 14


def test_recent_experiment_carries_its_latest_execution(client, engine, world):
    with scoped(engine) as s:
        batch = Batch(name="Sweep")
        s.add(batch)
        s.commit()
        batch_id = batch.id
    exp = add_experiment(engine, world, status="completed", batch_id=batch_id)
    started = now() - timedelta(minutes=5)
    add_execution(
        engine,
        exp,
        ["m-a", "m-b", "m-a"],
        status="completed",
        started_at=started,
        completed_at=started + timedelta(seconds=90),
        total_tokens=1200,
        total_cost_usd=0.5,
    )

    [recent] = client.get("/dashboard").json()["recent_experiments"]

    assert recent["id"] == exp
    assert recent["dataset_name"] == "answers"
    assert recent["batch_name"] == "Sweep"
    # Repeated models collapse, in pipeline order
    assert recent["models"] == [
        {"name": "m-a", "provider": "openai"},
        {"name": "m-b", "provider": "openai"},
    ]
    assert recent["duration_seconds"] == 90
    assert recent["total_tokens"] == 1200
    assert recent["total_cost_usd"] == 0.5
    # No results file yet
    assert recent["row_count"] is None


def test_experiment_without_execution_falls_back_to_configured_models(
    client, engine, world
):
    exp = add_experiment(engine, world, status="pending")
    with scoped(engine) as s:
        s.add_all(
            [
                ExperimentAgentConfig(
                    experiment_id=exp,
                    agent_id=world["agent"],
                    step_key=str(world["agent"]),
                    prompt_version_id=world["version"],
                    model_id=world["models"][1],
                    execution_order=0,
                ),
                # Inactive agents do not run
                ExperimentAgentConfig(
                    experiment_id=exp,
                    agent_id=world["other_agent"],
                    step_key=str(world["other_agent"]),
                    prompt_version_id=world["version"],
                    model_id=world["models"][0],
                    execution_order=1,
                    is_active=False,
                ),
            ]
        )
        s.commit()

    [recent] = client.get("/dashboard").json()["recent_experiments"]

    assert recent["models"] == [{"name": "m-b", "provider": "openai"}]
    assert recent["duration_seconds"] is None
    assert recent["total_cost_usd"] is None


def test_recent_experiments_are_newest_first_and_capped(client, engine, world):
    for i in range(8):
        add_experiment(engine, world, created_at=now() - timedelta(hours=8 - i))

    recent = client.get("/dashboard").json()["recent_experiments"]

    assert len(recent) == 5
    assert [r["id"] for r in recent] == [8, 7, 6, 5, 4]


def test_activity_counts_the_period_only(client, engine, world):
    old = add_experiment(
        engine, world, status="completed", created_at=now() - timedelta(days=30)
    )
    add_execution(
        engine,
        old,
        ["m-a"],
        started_at=now() - timedelta(days=30),
        total_tokens=999,
        total_cost_usd=9.0,
    )
    fresh = add_experiment(engine, world, status="completed")
    add_execution(
        engine,
        fresh,
        ["m-a"],
        total_tokens=100,
        total_cost_usd=0.25,
        rows_done=10,
        rows_failed=2,
    )
    add_experiment(engine, world, status="failed")
    add_experiment(engine, world, status="running")

    current = client.get("/dashboard").json()["activity"]["current"]

    assert current["experiments"] == 3
    assert current["completed"] == 1
    assert current["failed"] == 1
    assert current["total_tokens"] == 100
    assert current["total_cost_usd"] == 0.25
    assert current["rows_done"] == 10
    assert current["rows_failed"] == 2


def test_an_experiment_is_affected_when_its_latest_run_went_wrong(
    client, engine, world
):
    failed_rows = add_experiment(engine, world, status="completed")
    add_execution(
        engine, failed_rows, ["m-a"], status="completed", rows_done=10, rows_failed=2
    )
    failed = add_experiment(engine, world, status="failed")
    add_execution(engine, failed, ["m-a"], status="failed")
    running = add_experiment(engine, world, status="running")
    add_execution(
        engine, running, ["m-a"], status="running", rows_done=4, rows_failed=1
    )
    # Run again since, and clean this time: nothing left to look into
    fixed = add_experiment(engine, world, status="completed")
    add_execution(
        engine, fixed, ["m-a"], status="failed", started_at=now() - timedelta(hours=2)
    )
    add_execution(engine, fixed, ["m-a"], status="completed", rows_done=10)
    # Cancelling is a choice, not a problem, even with failed rows behind it
    cancelled = add_experiment(engine, world, status="cancelled")
    add_execution(
        engine, cancelled, ["m-a"], status="cancelled", rows_done=4, rows_failed=3
    )
    # Out of the period
    old = add_experiment(engine, world, status="failed")
    add_execution(
        engine, old, ["m-a"], status="failed", started_at=now() - timedelta(days=30)
    )

    current = client.get("/dashboard").json()["activity"]["current"]

    assert current["experiments_with_failures"] == 3


def test_active_lists_running_and_pending_experiments_however_old(
    client, engine, world
):
    running = add_experiment(
        engine, world, status="running", created_at=now() - timedelta(days=30)
    )
    pending = add_experiment(engine, world, status="pending")
    add_experiment(engine, world, status="completed")

    active = client.get("/dashboard").json()["activity"]["active"]

    # Newest first
    assert [a["id"] for a in active] == [pending, running]
    assert [a["status"] for a in active] == ["pending", "running"]


def test_previous_period_is_the_stretch_right_before(client, engine, world):
    for days_ago, tokens in ((2, 100), (10, 40), (20, 7)):
        exp = add_experiment(
            engine,
            world,
            status="completed",
            created_at=now() - timedelta(days=days_ago),
        )
        add_execution(
            engine,
            exp,
            ["m-a"],
            started_at=now() - timedelta(days=days_ago),
            total_tokens=tokens,
        )

    activity = client.get("/dashboard", params={"range": "7d"}).json()["activity"]

    assert activity["current"]["total_tokens"] == 100
    # 7 to 14 days ago: the 20-day-old one belongs to neither
    assert activity["previous"]["experiments"] == 1
    assert activity["previous"]["total_tokens"] == 40


def test_buckets_add_up_to_the_period(client, engine, world):
    for hours_ago in (1, 1, 30):
        exp = add_experiment(
            engine,
            world,
            status="completed",
            created_at=now() - timedelta(hours=hours_ago),
        )
        add_execution(
            engine,
            exp,
            ["m-a"],
            started_at=now() - timedelta(hours=hours_ago),
            total_tokens=10,
        )

    activity = client.get("/dashboard", params={"range": "7d"}).json()["activity"]
    buckets = activity["buckets"]

    assert (
        sum(b["experiments"] for b in buckets)
        == activity["current"]["experiments"]
        == 3
    )
    assert sum(b["total_tokens"] for b in buckets) == 30
    # Newest last: the two recent ones share the last slice
    assert buckets[-1]["experiments"] == 2
    assert [b["start"] for b in buckets] == sorted(b["start"] for b in buckets)


@pytest.mark.parametrize(
    ("range_", "slices"), [("24h", 12), ("7d", 14), ("30d", 15), ("90d", 15)]
)
def test_each_period_is_cut_in_its_own_slices(client, range_, slices):
    activity = client.get("/dashboard", params={"range": range_}).json()["activity"]

    assert activity["range"] == range_
    assert len(activity["buckets"]) == slices
    assert activity["previous"] is not None


def test_all_starts_at_the_first_experiment(client, engine, world):
    add_experiment(engine, world, created_at=now() - timedelta(days=400))
    add_experiment(engine, world)

    activity = client.get("/dashboard", params={"range": "all"}).json()["activity"]

    assert activity["since"] is None
    assert activity["current"]["experiments"] == 2
    assert 1 < len(activity["buckets"]) <= 16
    assert sum(b["experiments"] for b in activity["buckets"]) == 2


def test_all_is_compared_with_what_it_was_30_days_ago(client, engine, world):
    for days_ago in (400, 45, 2):
        exp = add_experiment(
            engine,
            world,
            status="completed",
            created_at=now() - timedelta(days=days_ago),
        )
        add_execution(
            engine,
            exp,
            ["m-a"],
            started_at=now() - timedelta(days=days_ago),
            total_tokens=10,
        )

    activity = client.get("/dashboard", params={"range": "all"}).json()["activity"]

    assert activity["current"]["experiments"] == 3
    assert activity["current"]["total_tokens"] == 30
    # Everything but the last 30 days
    assert activity["previous"]["experiments"] == 2
    assert activity["previous"]["total_tokens"] == 20


def test_all_has_nothing_to_compare_with_while_it_is_younger_than_30_days(
    client, engine, world
):
    add_experiment(engine, world, created_at=now() - timedelta(days=5))

    activity = client.get("/dashboard", params={"range": "all"}).json()["activity"]

    assert activity["previous"] is None


def test_unknown_range_is_rejected(client):
    assert client.get("/dashboard", params={"range": "1y"}).status_code == 422
