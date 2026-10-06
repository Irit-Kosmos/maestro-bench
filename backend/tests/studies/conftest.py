"""Fixtures and builders for the tests of studies and notes."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from api import analyses, batches, experiments, notes, studies, tags
from auth.workspaces import WorkspaceContext, workspace_context
from db import get_session
from tables import (
    Analysis,
    Batch,
    Dataset,
    Experiment,
    ExperimentExecution,
    User,
)
from tests.conftest import TEST_WORKSPACE_ID, scoped
from workspace_scope import scope_session


class Caller:
    """Who the requests come from: the app sets this from the signed-in user."""

    def __init__(self):
        self.user_id: int | None = None
        self.role = "owner"


@pytest.fixture
def caller():
    return Caller()


@pytest.fixture
def client(engine, caller):
    app = FastAPI()
    for module in (studies, notes, tags, experiments, batches, analyses):
        app.include_router(module.router)

    def _session():
        with Session(engine) as session:
            scope_session(session, TEST_WORKSPACE_ID, caller.user_id)
            yield session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[workspace_context] = lambda: WorkspaceContext(
        id=TEST_WORKSPACE_ID,
        slug="test",
        name="Test",
        role=caller.role,
        archived=False,
        user_id=caller.user_id or 0,
    )
    return TestClient(app)


@pytest.fixture
def alice(engine, caller):
    with Session(engine, expire_on_commit=False) as db:
        user = User(display_name="Alice")
        db.add(user)
        db.commit()
        caller.user_id = user.id
        return user


@pytest.fixture
def bob(engine):
    with Session(engine, expire_on_commit=False) as db:
        user = User(display_name="Bob")
        db.add(user)
        db.commit()
        return user


def make_experiment(
    engine, name="Run", *, batch_id=None, status="completed", executions=()
):
    """An experiment, with an execution for each (tokens, cost) given, oldest first."""
    with scoped(engine) as s:
        dataset = s.exec(select(Dataset)).first()
        if dataset is None:
            dataset = Dataset(name="answers", file_path="answers.csv")
            s.add(dataset)
            s.flush()
        experiment = Experiment(
            name=name,
            dataset_id=dataset.id,
            batch_id=batch_id,
            status=status,
            completed_at=datetime.now(UTC) if status == "completed" else None,
        )
        s.add(experiment)
        s.flush()
        start = datetime(2026, 1, 1, tzinfo=UTC)
        for n, (tokens, cost) in enumerate(executions):
            s.add(
                ExperimentExecution(
                    experiment_id=experiment.id,
                    status="completed",
                    dataset_snapshot=json.dumps({"name": "answers"}),
                    started_at=start + timedelta(hours=n),
                    total_tokens=tokens,
                    total_cost_usd=cost,
                )
            )
        s.commit()
        return experiment.id


def make_batch(engine, name="Grid"):
    with scoped(engine) as s:
        batch = Batch(name=name)
        s.add(batch)
        s.commit()
        return batch.id


def make_analysis(engine, name="Agreement"):
    with scoped(engine) as s:
        analysis = Analysis(
            name=name,
            config=json.dumps(
                {"truth_column": "t", "value_type": "numeric", "metrics": []}
            ),
            runs=json.dumps([]),
        )
        s.add(analysis)
        s.commit()
        return analysis.id


def make_study(client, name="Prompt v3", **extra):
    response = client.post("/studies", json={"name": name, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def ref(kind, item_id):
    return {"kind": kind, "item_id": item_id}
