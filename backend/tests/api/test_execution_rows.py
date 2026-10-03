import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from api import analyses
from db import get_session
from tables import ExperimentExecution

ROWS = [
    {
        "row_index": 1,
        "input_data": {"text": "great", "score": 5},
        "agents": [
            {"name": "Grader", "output": '```json\n{"score": 4}\n```', "error": None}
        ],
    },
    {
        "row_index": 2,
        "input_data": {"text": "bad", "score": 1},
        "agents": [{"name": "Grader", "output": None, "error": "timeout"}],
        "error": "timeout",
    },
]


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
    app.include_router(analyses.router)

    def _session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _session
    return TestClient(app)


def _add_execution(engine, results_file: str | None) -> int:
    with Session(engine) as s:
        execution = ExperimentExecution(
            experiment_id=1,
            dataset_snapshot="{}",
            results_file_path=results_file,
        )
        s.add(execution)
        s.commit()
        return execution.id


def _results_file(tmp_path, rows=ROWS) -> str:
    path = tmp_path / "results.json"
    path.write_text(json.dumps({"rows": rows}))
    return str(path)


def test_returns_input_and_parsed_agent_output(client, engine, tmp_path):
    execution_id = _add_execution(engine, _results_file(tmp_path))

    response = client.get(f"/executions/{execution_id}/rows/1")

    assert response.status_code == 200
    body = response.json()
    assert body["row_index"] == 1
    assert body["input_data"] == {"text": "great", "score": 5}
    assert body["agents"] == [{"name": "Grader", "output": {"score": 4}, "error": None}]


def test_carries_agent_and_row_errors(client, engine, tmp_path):
    execution_id = _add_execution(engine, _results_file(tmp_path))

    body = client.get(f"/executions/{execution_id}/rows/2").json()

    assert body["error"] == "timeout"
    assert body["agents"][0]["error"] == "timeout"


def test_unknown_row_is_404(client, engine, tmp_path):
    execution_id = _add_execution(engine, _results_file(tmp_path))

    assert client.get(f"/executions/{execution_id}/rows/99").status_code == 404


def test_unknown_execution_is_404(client):
    assert client.get("/executions/42/rows/1").status_code == 404


def test_execution_without_results_file_is_404(client, engine):
    execution_id = _add_execution(engine, None)

    assert client.get(f"/executions/{execution_id}/rows/1").status_code == 404
