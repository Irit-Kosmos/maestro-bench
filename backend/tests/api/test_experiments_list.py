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

from datetime import UTC, datetime, timedelta

import pytest

from api import experiments
from tables import Dataset, Experiment, ExperimentExecution
from tests.conftest import api_client, scoped


def now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def client(engine):
    return api_client(engine, experiments)


def add_experiment(engine) -> int:
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        s.add(dataset)
        s.flush()
        experiment = Experiment(name="Run", dataset_id=dataset.id)
        s.add(experiment)
        s.commit()
        return experiment.id


def add_execution(engine, experiment_id, **fields) -> int:
    with scoped(engine) as s:
        execution = ExperimentExecution(
            experiment_id=experiment_id, dataset_snapshot="{}", **fields
        )
        s.add(execution)
        s.commit()
        return execution.id


def test_nothing_run_yet(client, engine):
    add_experiment(engine)

    [listed] = client.get("/experiments").json()

    assert listed["last_run_at"] is None
    assert listed["latest_analyzable_execution_id"] is None


def test_the_last_run_is_the_latest_execution_whatever_its_status(client, engine):
    experiment = add_experiment(engine)
    add_execution(
        engine, experiment, status="completed", started_at=now() - timedelta(days=3)
    )
    add_execution(
        engine, experiment, status="failed", started_at=now() - timedelta(hours=1)
    )

    [listed] = client.get("/experiments").json()

    assert datetime.fromisoformat(listed["last_run_at"]) > now() - timedelta(hours=2)


def test_the_latest_analyzable_execution_completed_and_kept_its_results(client, engine):
    experiment = add_experiment(engine)
    analyzable = add_execution(
        engine,
        experiment,
        status="completed",
        results_file_path="results.csv",
        started_at=now() - timedelta(days=3),
    )
    # Completed without results, then failed with partial ones: neither can be read
    add_execution(
        engine, experiment, status="completed", started_at=now() - timedelta(days=2)
    )
    add_execution(
        engine,
        experiment,
        status="failed",
        results_file_path="partial.csv",
        started_at=now() - timedelta(days=1),
    )

    [listed] = client.get("/experiments").json()

    assert listed["latest_analyzable_execution_id"] == analyzable
