# MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
# Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
# Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import json

import pytest

from api import experiment_executions
from tables import Dataset, Experiment, ExperimentExecution
from tests.conftest import api_client, scoped


def _ok(row_index: int) -> dict:
    return {
        "row_index": row_index,
        "input_data": {},
        "agents": [{"name": "Grader", "step_key": "1", "output": "4", "error": None}],
        "error": None,
    }


def _agent_failed(row_index: int, error: str, name: str = "Grader", step: str = "1") -> dict:
    return {
        "row_index": row_index,
        "input_data": {},
        "agents": [
            {"name": "Reader", "step_key": "2", "output": "ok", "error": None},
            {"name": name, "step_key": step, "output": None, "error": error},
        ],
        "error": f"Agent '{name}' failed: {error}",
    }


def _row_failed(row_index: int, error: str) -> dict:
    return {"row_index": row_index, "input_data": {}, "agents": [], "error": error}


@pytest.fixture
def client(engine):
    return api_client(engine, experiment_executions)


def _add_execution(engine, results_file: str | None, **fields) -> int:
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
            **fields,
        )
        s.add(execution)
        s.commit()
        return execution.id


def _results_file(results_dir, rows) -> str:
    path = results_dir / "results.json"
    path.write_text(json.dumps({"rows": rows}))
    return path.name


def test_groups_rows_by_failing_step_and_error_most_rows_first(client, engine, results_dir):
    rows = [
        _ok(1),
        _agent_failed(2, "timeout"),
        _row_failed(3, "bad row"),
        _agent_failed(4, "rate limited"),
        _agent_failed(5, "rate limited"),
        _agent_failed(6, "timeout", name="Judge", step="3"),
        _agent_failed(7, "rate limited"),
    ]
    execution_id = _add_execution(engine, _results_file(results_dir, rows))

    body = client.get(f"/executions/{execution_id}/failures").json()

    assert body["failed_rows"] == 6
    assert body["groups"][0] == {
        "message": "rate limited",
        "agent_name": "Grader",
        "step_key": "1",
        "rows": [4, 5, 7],
    }
    # The same error on another step is another group
    rest = sorted((g["agent_name"] or "", g["message"], g["rows"]) for g in body["groups"][1:])
    assert rest == [("", "bad row", [3]), ("Grader", "timeout", [2]), ("Judge", "timeout", [6])]


def test_no_failure_gives_no_group(client, engine, results_dir):
    execution_id = _add_execution(engine, _results_file(results_dir, [_ok(1), _ok(2)]))

    assert client.get(f"/executions/{execution_id}/failures").json() == {
        "failed_rows": 0,
        "groups": [],
    }


def test_execution_without_results_file_has_no_group(client, engine):
    execution_id = _add_execution(engine, None)

    body = client.get(f"/executions/{execution_id}/failures").json()

    assert body == {"failed_rows": 0, "groups": []}


def test_unknown_execution_is_404(client):
    assert client.get("/executions/42/failures").status_code == 404


def test_execution_shows_its_row_counts_and_run_error(client, engine):
    execution_id = _add_execution(
        engine, None, status="failed", rows_done=10, rows_failed=3, error="crashed"
    )

    body = client.get(f"/executions/{execution_id}").json()

    assert (body["rows_done"], body["rows_failed"], body["error"]) == (10, 3, "crashed")
