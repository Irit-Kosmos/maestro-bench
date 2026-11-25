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

import io
import json
import zipfile
from datetime import UTC, datetime, timedelta

import pytest

from api import downloads
from results_export import slug
from tables import Batch, Dataset, Experiment, ExperimentExecution
from tests.conftest import api_client, scoped

T0 = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def client(engine):
    return api_client(engine, downloads)


@pytest.fixture
def world(engine, results_dir):
    """Batch `Grid` (two experiments with results, one still running) and two lone experiments."""

    def results(name: str, content: dict) -> str:
        (results_dir / name).write_text(json.dumps(content))
        return name

    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        s.add(dataset)
        s.flush()
        grid = Batch(name="Mistral Large 4")
        other = Batch(name="Other")
        s.add_all([grid, other])
        s.flush()

        def experiment(name, batch=None, runs=()):
            row = Experiment(name=name, dataset_id=dataset.id, batch_id=batch.id if batch else None)
            s.add(row)
            s.flush()
            for minutes, status, path in runs:
                s.add(
                    ExperimentExecution(
                        experiment_id=row.id,
                        status=status,
                        started_at=T0 + timedelta(minutes=minutes),
                        dataset_snapshot="{}",
                        results_file_path=path,
                    )
                )
            s.flush()
            return row.id

        ids = {
            "grid": grid.id,
            "other": other.id,
            # Re-run: the latest completed execution counts, not the one still running
            "elaastic": experiment(
                "Mistral Large 4 · Elaastic",
                grid,
                [
                    (0, "completed", results("old.json", {"run": "old"})),
                    (5, "completed", results("new.json", {"run": "new"})),
                    (9, "running", None),
                ],
            ),
            "mohler": experiment(
                "Mistral Large 4 · Mohler", grid, [(0, "completed", results("m.json", {"run": "m"}))]
            ),
            "failed": experiment("Mistral Large 4 · Broken", grid, [(0, "failed", None)]),
            "elsewhere": experiment(
                "Other · A", other, [(0, "completed", results("o.json", {"run": "o"}))]
            ),
            "solo": experiment("Solo run", None, [(0, "completed", results("s.json", {"run": "s"}))]),
            "lost": experiment("Lost", None, [(0, "completed", "missing.json")]),
        }
        s.commit()
    return ids


def unzip(response) -> dict[str, dict]:
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.testzip() is None
        return {name: json.loads(archive.read(name)) for name in archive.namelist()}


def test_a_batch_brings_the_latest_completed_results_of_its_experiments(client, world):
    response = client.get(f"/batches/{world['grid']}/results")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    folder = f"mistral-large-4_batch-{world['grid']}"
    assert f'filename="{folder}.zip"' in response.headers["content-disposition"]
    assert unzip(response) == {
        f"{folder}/elaastic_exp-{world['elaastic']}.json": {"run": "new"},
        f"{folder}/mohler_exp-{world['mohler']}.json": {"run": "m"},
    }
    # The failed experiment had nothing to bring
    assert response.headers["x-skipped-experiments"] == "1"


def test_a_selection_puts_each_experiment_in_the_folder_of_its_batch(client, world):
    response = client.get(
        "/results/download",
        params={
            "batch_id": [world["other"]],
            "experiment_id": [world["mohler"], world["solo"], world["lost"]],
        },
    )

    assert response.status_code == 200
    assert "maestro-results_" in response.headers["content-disposition"]
    assert set(unzip(response)) == {
        f"mistral-large-4_batch-{world['grid']}/mohler_exp-{world['mohler']}.json",
        f"other_batch-{world['other']}/a_exp-{world['elsewhere']}.json",
        f"experiments/solo-run_exp-{world['solo']}.json",
    }
    # Its results file is not on disk anymore
    assert response.headers["x-skipped-experiments"] == "1"


def test_experiments_of_one_batch_are_named_after_it(client, world):
    response = client.get(
        "/results/download", params={"experiment_id": [world["elaastic"], world["mohler"]]}
    )

    assert f"mistral-large-4_batch-{world['grid']}.zip" in response.headers["content-disposition"]
    assert response.headers["x-skipped-experiments"] == "0"


def test_nothing_to_download_is_an_error(client, world):
    response = client.get("/results/download", params={"experiment_id": [world["failed"]]})
    assert response.status_code == 404

    assert client.get("/results/download").status_code == 422
    assert client.get("/results/download", params={"batch_id": [999]}).status_code == 404
    assert client.get("/results/download", params={"experiment_id": [999]}).status_code == 404
    assert client.get("/batches/999/results").status_code == 404


def test_too_many_batches_at_once_are_refused(client, world):
    params = {"batch_id": list(range(1, downloads.MAX_BATCHES + 2))}
    assert client.get("/results/download", params=params).status_code == 422


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Mistral Large 4", "mistral-large-4"),
        ("Température 0.7 / v2", "température-0-7-v2"),
        ("../../etc", "etc"),
        ("···", "fallback"),
    ],
)
def test_names_are_safe_in_a_file_name(name, expected):
    assert slug(name, "fallback") == expected
