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

from api.events import _running_states, _wanted
from schemas.events import RunState
from tables import Batch, Dataset, Experiment, ExperimentExecution


def add_execution(session, *, batch_id=None, **fields) -> ExperimentExecution:
    dataset = Dataset(name="answers", file_path="answers.csv")
    session.add(dataset)
    session.flush()
    experiment = Experiment(name="Run", dataset_id=dataset.id, batch_id=batch_id)
    session.add(experiment)
    session.flush()
    execution = ExperimentExecution(
        experiment_id=experiment.id, dataset_snapshot="{}", **fields
    )
    session.add(execution)
    session.commit()
    return execution


def test_snapshot_lists_running_executions_with_their_counters(session):
    batch = Batch(name="Grid")
    session.add(batch)
    session.flush()
    running = add_execution(
        session, batch_id=batch.id, rows_total=10, rows_done=4, rows_failed=1
    )
    add_execution(session, status="completed")

    assert _running_states(session) == [
        RunState(
            experiment_id=running.experiment_id,
            batch_id=batch.id,
            execution_id=running.id,
            status="running",
            rows_total=10,
            rows_done=4,
            rows_failed=1,
        )
    ]


def test_snapshot_is_empty_without_running_execution(session):
    add_execution(session, status="cancelled")

    assert _running_states(session) == []


def test_filters_on_experiment_and_batch():
    state = RunState(experiment_id=3, batch_id=7, status="running")

    assert _wanted(state, None, None)
    assert _wanted(state, 3, None)
    assert _wanted(state, None, 7)
    assert not _wanted(state, 4, None)
    assert not _wanted(state, None, 8)
