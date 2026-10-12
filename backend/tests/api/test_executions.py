import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from api import experiment_executions
from db import get_session
from tables import (
    Agent,
    AgentExecutionSnapshot,
    Batch,
    Dataset,
    Experiment,
    ExperimentExecution,
)
from tests.conftest import TEST_WORKSPACE_ID, scoped
from workspace_scope import scope_session


def now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def client(engine):
    app = FastAPI()
    app.include_router(experiment_executions.router)

    def _session():
        with Session(engine) as session:
            scope_session(session, TEST_WORKSPACE_ID)
            yield session

    app.dependency_overrides[get_session] = _session
    return TestClient(app)


def add_experiment(engine, name="Run", **fields) -> int:
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        s.add(dataset)
        s.flush()
        experiment = Experiment(name=name, dataset_id=dataset.id, **fields)
        s.add(experiment)
        s.commit()
        return experiment.id


def add_agent(engine, name="Grader") -> int:
    with scoped(engine) as s:
        agent = Agent(name=name)
        s.add(agent)
        s.commit()
        return agent.id


def add_execution(engine, experiment_id, agents=(), agent_id=None, **fields) -> int:
    """An execution with one agent snapshot per (agent, model) pair."""
    if agents and agent_id is None:
        agent_id = add_agent(engine)
    fields.setdefault("dataset_snapshot", json.dumps({"name": "answers"}))
    with scoped(engine) as s:
        execution = ExperimentExecution(experiment_id=experiment_id, **fields)
        s.add(execution)
        s.flush()
        for order, (agent, model) in enumerate(agents):
            s.add(
                AgentExecutionSnapshot(
                    execution_id=execution.id,
                    agent_id=agent_id,
                    agent_name_snapshot=agent,
                    model_name_snapshot=model,
                    model_provider_snapshot="openai",
                    prompt_name_snapshot="Grader",
                    prompt_version_snapshot="2",
                    execution_order=order,
                )
            )
        s.commit()
        return execution.id


def test_no_executions(client):
    assert client.get("/executions").json() == []


def test_lists_every_status_newest_first(client, engine):
    exp = add_experiment(engine)
    ids = [
        add_execution(
            engine, exp, status=status, started_at=now() - timedelta(hours=hours)
        )
        for status, hours in [
            ("completed", 5),
            ("failed", 3),
            ("cancelled", 4),
            ("running", 1),
        ]
    ]

    listed = client.get("/executions").json()

    assert [e["id"] for e in listed] == [ids[3], ids[1], ids[2], ids[0]]
    assert [e["status"] for e in listed] == [
        "running",
        "failed",
        "cancelled",
        "completed",
    ]


def test_an_execution_carries_its_experiment_dataset_and_batch(client, engine):
    with scoped(engine) as s:
        batch = Batch(name="Sweep")
        s.add(batch)
        s.commit()
        batch_id = batch.id
    exp = add_experiment(engine, name="Grade answers", batch_id=batch_id)
    add_execution(engine, exp)

    [execution] = client.get("/executions").json()

    assert execution["experiment_id"] == exp
    assert execution["experiment_name"] == "Grade answers"
    assert execution["batch_id"] == batch_id
    assert execution["batch_name"] == "Sweep"
    assert execution["dataset_name"] == "answers"


def test_agents_are_listed_in_the_order_they_ran(client, engine):
    exp = add_experiment(engine)
    add_execution(engine, exp, agents=[("Extractor", "m-a"), ("Grader", "m-b")])

    [execution] = client.get("/executions").json()

    assert [(a["name"], a["model"]) for a in execution["agents"]] == [
        ("Extractor", "m-a"),
        ("Grader", "m-b"),
    ]
    assert execution["agents"][0]["provider"] == "openai"
    assert execution["agents"][0]["prompt"] == "Grader"
    assert execution["agents"][0]["prompt_version"] == "2"


def test_figures_and_progress(client, engine, results_dir):
    exp = add_experiment(engine)
    started = now() - timedelta(minutes=10)
    results = results_dir / "results.json"
    results.write_text("{}")
    add_execution(
        engine,
        exp,
        status="completed",
        started_at=started,
        completed_at=started + timedelta(seconds=90),
        rows_total=20,
        rows_done=20,
        rows_failed=3,
        total_tokens=1200,
        total_cost_usd=0.5,
        results_file_path=results.name,
    )
    add_execution(engine, exp, status="running", rows_total=20, rows_done=4)

    running, finished = client.get("/executions").json()

    assert finished["duration_seconds"] == 90
    assert finished["rows_failed"] == 3
    assert finished["total_tokens"] == 1200
    assert finished["total_cost_usd"] == 0.5
    assert finished["has_results"] is True
    # No duration, and nothing to download, until it has ended
    assert running["duration_seconds"] is None
    assert running["has_results"] is False
    assert (running["rows_total"], running["rows_done"]) == (20, 4)


def test_a_deleted_agent_has_no_id_to_link_to(client, engine):
    alive = add_agent(engine)
    doomed = add_agent(engine, "Gone")
    exp = add_experiment(engine)
    kept = add_execution(engine, exp, agents=[("Grader", "m-a")], agent_id=alive)
    orphaned = add_execution(engine, exp, agents=[("Gone", "m-a")], agent_id=doomed)

    # The database clears the snapshot's link; the snapshot itself stays
    with scoped(engine) as s:
        s.delete(s.get(Agent, doomed))
        s.commit()

    listed = {e["id"]: e for e in client.get("/executions").json()}

    assert listed[kept]["agents"][0]["agent_id"] == alive
    assert listed[orphaned]["agents"][0]["agent_id"] is None
    assert listed[orphaned]["agents"][0]["name"] == "Gone"
