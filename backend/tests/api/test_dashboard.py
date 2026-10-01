from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from api import dashboard
from db import get_session
from tables import (
    Agent,
    AgentExecutionSnapshot,
    AgentTeam,
    Batch,
    Dataset,
    Experiment,
    ExperimentAgentConfig,
    ExperimentExecution,
    Model,
    Prompt,
    PromptVersion,
)


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(engine):
    app = FastAPI()
    app.include_router(dashboard.router)

    def _session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _session
    return TestClient(app)


@pytest.fixture
def world(engine):
    with Session(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        team = AgentTeam(name="Graders")
        prompt = Prompt(name="Grader")
        s.add_all([dataset, team, prompt])
        s.flush()
        version = PromptVersion(prompt_id=prompt.id, version="1")
        models = [Model(name=n, provider="openai") for n in ("m-a", "m-b")]
        s.add_all([version, *models])
        s.flush()
        agent = Agent(name="Grader", team_id=team.id)
        s.add(agent)
        s.commit()
        return {
            "dataset": dataset.id,
            "agent": agent.id,
            "version": version.id,
            "models": [m.id for m in models],
        }


def add_experiment(engine, world, **fields) -> int:
    with Session(engine) as s:
        experiment = Experiment(name="Run", dataset_id=world["dataset"], **fields)
        s.add(experiment)
        s.commit()
        return experiment.id


def add_execution(engine, experiment_id, models, **fields) -> int:
    """An execution with one agent snapshot per model name."""
    with Session(engine) as s:
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
    assert body["activity"] == {
        "days": 7,
        "experiments": 0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "active": 0,
    }


def test_recent_experiment_carries_its_latest_execution(client, engine, world):
    with Session(engine) as s:
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
    assert recent["models"] == ["m-a", "m-b"]
    assert recent["duration_seconds"] == 90
    assert recent["total_tokens"] == 1200
    assert recent["total_cost_usd"] == 0.5
    # No results file yet
    assert recent["row_count"] is None


def test_experiment_without_execution_falls_back_to_configured_models(
    client, engine, world
):
    exp = add_experiment(engine, world, status="pending")
    with Session(engine) as s:
        s.add_all(
            [
                ExperimentAgentConfig(
                    experiment_id=exp,
                    agent_id=world["agent"],
                    prompt_version_id=world["version"],
                    model_id=world["models"][1],
                    execution_order=0,
                ),
                # Inactive agents do not run
                ExperimentAgentConfig(
                    experiment_id=exp,
                    agent_id=world["agent"] + 1,
                    prompt_version_id=world["version"],
                    model_id=world["models"][0],
                    execution_order=1,
                    is_active=False,
                ),
            ]
        )
        s.commit()

    [recent] = client.get("/dashboard").json()["recent_experiments"]

    assert recent["models"] == ["m-b"]
    assert recent["duration_seconds"] is None
    assert recent["total_cost_usd"] is None


def test_recent_experiments_are_newest_first_and_capped(client, engine, world):
    for i in range(8):
        add_experiment(engine, world, created_at=now() - timedelta(hours=8 - i))

    recent = client.get("/dashboard").json()["recent_experiments"]

    assert len(recent) == 5
    assert [r["id"] for r in recent] == [8, 7, 6, 5, 4]


def test_activity_counts_the_last_week_only(client, engine, world):
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
    add_execution(engine, fresh, ["m-a"], total_tokens=100, total_cost_usd=0.25)
    add_experiment(engine, world, status="running")
    add_experiment(engine, world, status="pending")

    activity = client.get("/dashboard").json()["activity"]

    assert activity["experiments"] == 3
    assert activity["total_tokens"] == 100
    assert activity["total_cost_usd"] == 0.25
    # Active counts running and pending experiments, however old
    assert activity["active"] == 2
