import json

import pytest

from api import analyses
from tables import Dataset, Experiment, ExperimentExecution
from tests.conftest import api_client, scoped

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
def client(engine):
    return api_client(engine, analyses)


def _add_execution(engine, results_file: str | None) -> int:
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        s.add(dataset)
        s.flush()
        experiment = Experiment(name="Run", dataset_id=dataset.id)
        s.add(experiment)
        s.flush()
        execution = ExperimentExecution(
            experiment_id=experiment.id,
            dataset_snapshot="{}",
            results_file_path=results_file,
        )
        s.add(execution)
        s.commit()
        return execution.id


def _results_file(results_dir, rows=ROWS) -> str:
    path = results_dir / "results.json"
    path.write_text(json.dumps({"rows": rows}))
    return path.name


def test_returns_input_and_parsed_agent_output(client, engine, results_dir):
    execution_id = _add_execution(engine, _results_file(results_dir))

    response = client.get(f"/executions/{execution_id}/rows/1")

    assert response.status_code == 200
    body = response.json()
    assert body["row_index"] == 1
    assert body["input_data"] == {"text": "great", "score": 5}
    assert body["agents"] == [
        {
            "name": "Grader",
            "kind": "llm",
            "inputs": None,
            "output": {"score": 4},
            "error": None,
        }
    ]


def test_aggregator_rows_carry_their_inputs(client, engine, results_dir):
    rows = [
        {
            "row_index": 1,
            "input_data": {},
            "agents": [
                {
                    "name": "Final",
                    "kind": "aggregator",
                    "inputs": {"a": 3, "w": 0.5},
                    "output": {"score": 1.5},
                    "error": None,
                }
            ],
        }
    ]
    execution_id = _add_execution(engine, _results_file(results_dir, rows))

    agent = client.get(f"/executions/{execution_id}/rows/1").json()["agents"][0]

    assert agent["kind"] == "aggregator"
    assert agent["inputs"] == {"a": 3, "w": 0.5}


def test_carries_agent_and_row_errors(client, engine, results_dir):
    execution_id = _add_execution(engine, _results_file(results_dir))

    body = client.get(f"/executions/{execution_id}/rows/2").json()

    assert body["error"] == "timeout"
    assert body["agents"][0]["error"] == "timeout"


def test_unknown_row_is_404(client, engine, results_dir):
    execution_id = _add_execution(engine, _results_file(results_dir))

    assert client.get(f"/executions/{execution_id}/rows/99").status_code == 404


def test_unknown_execution_is_404(client):
    assert client.get("/executions/42/rows/1").status_code == 404


def test_execution_without_results_file_is_404(client, engine):
    execution_id = _add_execution(engine, None)

    assert client.get(f"/executions/{execution_id}/rows/1").status_code == 404
