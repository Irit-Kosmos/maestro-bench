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

import pandas as pd

import experiment_utils
from experiment_utils import apply_dataset_sampling, create_execution_snapshot
from tables import Batch, Dataset, Experiment


def make_experiment(session, *, batch=None, sampling_type="random"):
    dataset = session.get(Dataset, 1) or Dataset(name="d", file_path="d.csv")
    session.add(dataset)
    session.flush()
    experiment = Experiment(
        name="e",
        dataset_id=dataset.id,
        sampling_type=sampling_type,
        sampling_size=10,
        batch_id=batch.id if batch else None,
    )
    session.add(experiment)
    session.commit()
    return experiment


def seed_of(execution) -> int | None:
    return json.loads(execution.dataset_snapshot)["sampling_config"]["sampling_seed"]


class TestBatchSampling:
    def test_experiments_of_a_batch_draw_the_same_rows(self, session):
        batch = Batch(name="b", sampling_seed=1234)
        session.add(batch)
        session.commit()

        seeds = {
            seed_of(create_execution_snapshot(make_experiment(session, batch=batch).id, session))
            for _ in range(3)
        }

        assert seeds == {1234}

    def test_a_rerun_in_the_batch_keeps_the_batch_sample(self, session):
        batch = Batch(name="b", sampling_seed=99)
        session.add(batch)
        session.commit()
        experiment = make_experiment(session, batch=batch)

        first = create_execution_snapshot(experiment.id, session)
        second = create_execution_snapshot(experiment.id, session)

        assert seed_of(first) == seed_of(second) == 99

    def test_a_standalone_experiment_keeps_its_sample_between_runs(self, session):
        experiment = make_experiment(session)

        seeds = {seed_of(create_execution_snapshot(experiment.id, session)) for _ in range(3)}

        assert len(seeds) == 1
        assert seeds == {experiment.sampling_seed}

    def test_standalone_experiments_still_draw_their_own_sample(self, session):
        seeds = {
            seed_of(create_execution_snapshot(make_experiment(session).id, session))
            for _ in range(5)
        }

        assert len(seeds) > 1

    def test_no_seed_without_random_sampling(self, session):
        batch = Batch(name="b", sampling_seed=7)
        session.add(batch)
        session.commit()
        experiment = make_experiment(session, batch=batch, sampling_type="all")

        assert seed_of(create_execution_snapshot(experiment.id, session)) is None

    def test_same_seed_means_same_rows(self, tmp_path, monkeypatch):
        path = tmp_path / "d.csv"
        pd.DataFrame({"x": range(100)}).to_csv(path, index=False)
        monkeypatch.setattr(experiment_utils, "validate_dataset_file", lambda *_: path)
        config = {"sampling_type": "random", "sampling_size": 10, "sampling_seed": 5}

        first = apply_dataset_sampling(1, "d.csv", config)
        second = apply_dataset_sampling(1, "d.csv", config)

        assert list(first.index) == list(second.index)
