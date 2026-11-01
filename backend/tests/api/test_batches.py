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
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlmodel import select

import async_jobs
from api import batches, experiments
from experiment_utils import create_execution_snapshot
from tables import (
    Agent,
    Batch,
    Dataset,
    Experiment,
    ExperimentAgentConfig,
    ExperimentExecution,
    Model,
    Prompt,
    PromptVersion,
)
from tests.conftest import api_client, scoped

REAL_START_EXPERIMENT = async_jobs.start_experiment


@pytest.fixture
def jobs(monkeypatch):
    """Experiments handed to the background runner, instead of running."""
    jobs = SimpleNamespace(started=[], cancelled=[])
    monkeypatch.setattr(
        async_jobs,
        "start_experiment",
        lambda eid, workspace_id, launched_by=None: jobs.started.append(eid) or "started",
    )
    monkeypatch.setattr(
        async_jobs, "cancel_experiment", lambda eid: jobs.cancelled.append(eid) or True
    )
    return jobs


@pytest.fixture
def client(engine, jobs):
    return api_client(engine, batches, experiments)


@pytest.fixture
def world(engine):
    """A dataset, an agent with two prompt versions and three models."""
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        prompt = Prompt(name="Grader")
        s.add_all([dataset, prompt])
        s.flush()
        v1 = PromptVersion(
            prompt_id=prompt.id, version="1", variables='["answer"]'
        )
        v2 = PromptVersion(
            prompt_id=prompt.id, version="2", variables='["answer"]'
        )
        v3 = PromptVersion(
            prompt_id=prompt.id, version="3", variables='["answer", "reference"]'
        )
        models = [
            Model(name=name, provider="openai") for name in ("m-a", "m-b", "m-c")
        ]
        s.add_all([v1, v2, v3, *models])
        s.flush()
        agent = Agent(
            name="Grader",
            default_prompt_version_id=v1.id,
            default_model_id=models[0].id,
        )
        s.add(agent)
        s.commit()
        return {
            "dataset": dataset.id,
            "agent": agent.id,
            "v1": v1.id,
            "v2": v2.id,
            "v3": v3.id,
            "models": [m.id for m in models],
        }


def payload(world, variations, **config_overrides):
    agent_config = {
        "is_active": True,
        "prompt_version_id": world["v1"],
        "model_id": world["models"][0],
        "input_mappings": [
            {"variable": "answer", "source": "dataset", "sourceColumn": "text"}
        ],
        **config_overrides,
    }
    return {
        "name": "Compare",
        "config": {
            "dataset_id": world["dataset"],
            "agent_configurations": {str(world["agent"]): agent_config},
            "sampling_type": "all",
        },
        "variations": variations,
    }


def model_axis(world, *indexes):
    return {
        "agent_id": world["agent"],
        "field": "model_id",
        "values": [world["models"][i] for i in indexes],
    }


class TestCreateBatch:
    def test_one_experiment_per_value_all_started(self, client, world, jobs):
        response = client.post(
            "/batches", json=payload(world, [model_axis(world, 0, 1, 2)])
        )

        assert response.status_code == 201
        body = response.json()
        assert [e["name"] for e in body["experiments"]] == [
            "Compare · m-a",
            "Compare · m-b",
            "Compare · m-c",
        ]
        assert sorted(jobs.started) == sorted(e["id"] for e in body["experiments"])

    def test_each_experiment_uses_its_own_value(self, client, world, engine):
        client.post("/batches", json=payload(world, [model_axis(world, 1, 2)]))

        with scoped(engine) as s:
            configs = s.exec(
                select(ExperimentAgentConfig).order_by(ExperimentAgentConfig.id)
            ).all()
        assert [c.model_id for c in configs] == [
            world["models"][1],
            world["models"][2],
        ]
        # Everything else is shared
        assert {c.prompt_version_id for c in configs} == {world["v1"]}
        assert all(json.loads(c.input_mappings)[0]["variable"] == "answer" for c in configs)

    def test_two_axes_make_a_grid(self, client, world):
        variations = [
            model_axis(world, 0, 1),
            {
                "agent_id": world["agent"],
                "field": "prompt_version_id",
                "values": [world["v1"], world["v2"]],
            },
        ]
        body = client.post("/batches", json=payload(world, variations)).json()

        assert len(body["experiments"]) == 4
        assert body["experiments"][0]["name"] == "Compare · m-a · Grader v1"

    def test_zero_temperature_is_kept(self, client, world, engine):
        variations = [
            {
                "agent_id": world["agent"],
                "field": "temperature",
                "values": [0, 0.7],
            }
        ]
        client.post("/batches", json=payload(world, variations))

        with scoped(engine) as s:
            temperatures = [
                c.temperature
                for c in s.exec(
                    select(ExperimentAgentConfig).order_by(ExperimentAgentConfig.id)
                ).all()
            ]
        assert temperatures == [0, 0.7]

    def test_records_the_base_experiment_outside_the_batch(
        self, client, world, engine
    ):
        with scoped(engine) as s:
            base = Experiment(name="Base", dataset_id=world["dataset"])
            s.add(base)
            s.commit()
            base_id = base.id

        data = payload(world, [model_axis(world, 1, 2)])
        data["base_experiment_id"] = base_id
        body = client.post("/batches", json=data).json()

        assert body["base_experiment_id"] == base_id
        assert body["base_experiment_name"] == "Base"
        assert base_id not in [e["id"] for e in body["experiments"]]

    def test_random_sampling_gets_one_seed_for_the_batch(self, client, world, engine):
        data = payload(world, [model_axis(world, 0, 1)])
        data["config"].update(sampling_type="random", sampling_size=5)
        batch_id = client.post("/batches", json=data).json()["id"]

        with scoped(engine) as s:
            assert s.get(Batch, batch_id).sampling_seed is not None

    def test_random_sampling_takes_the_seed_it_is_given(self, client, world, engine):
        data = payload(world, [model_axis(world, 0, 1)])
        data["config"].update(sampling_type="random", sampling_size=5, sampling_seed=42)
        body = client.post("/batches", json=data).json()

        with scoped(engine) as s:
            assert s.get(Batch, body["id"]).sampling_seed == 42
        exp_id = body["experiments"][0]["id"]
        assert client.get(f"/experiments/{exp_id}").json()["sampling_seed"] == 42

    def test_a_seed_is_a_whole_number_pandas_accepts(self, client, world):
        for seed in (-1, 2**32):
            data = payload(world, [model_axis(world, 0, 1)])
            data["config"].update(
                sampling_type="random", sampling_size=5, sampling_seed=seed
            )
            assert client.post("/batches", json=data).status_code == 422

    def test_no_seed_when_the_sample_is_not_random(self, client, world, engine):
        batch_id = client.post(
            "/batches", json=payload(world, [model_axis(world, 0, 1)])
        ).json()["id"]

        with scoped(engine) as s:
            assert s.get(Batch, batch_id).sampling_seed is None

    def test_experiments_know_their_batch(self, client, world):
        body = client.post(
            "/batches", json=payload(world, [model_axis(world, 0, 1)])
        ).json()

        experiment = client.get(f"/experiments/{body['experiments'][1]['id']}").json()

        assert experiment["batch_id"] == body["id"]
        assert experiment["batch_name"] == "Compare"


class TestRepeatedAgent:
    """The same agent may run twice in the pipeline; each run is its own axis."""

    def twice(self, world):
        step = f"{world['agent']}#2"
        body = payload(world, [])
        configs = body["config"]["agent_configurations"]
        configs[step] = {**configs[str(world["agent"])], "execution_order": 2}
        body["variations"] = [
            {
                "step_key": str(world["agent"]),
                "field": "model_id",
                "values": [world["models"][0], world["models"][1]],
            },
            {"step_key": step, "field": "model_id", "values": [world["models"][2]]},
        ]
        return body

    def test_each_step_varies_on_its_own(self, client, world, engine):
        response = client.post("/batches", json=self.twice(world))

        assert response.status_code == 201, response.text
        body = response.json()
        assert [v["step_key"] for v in body["variations"]] == [
            str(world["agent"]),
            f"{world['agent']}#2",
        ]
        assert [v["agent_name"] for v in body["variations"]] == ["Grader", "Grader #2"]
        assert [e["name"] for e in body["experiments"]] == [
            "Compare · Grader: m-a · Grader #2: m-c",
            "Compare · Grader: m-b · Grader #2: m-c",
        ]
        with scoped(engine) as s:
            configs = s.exec(
                select(ExperimentAgentConfig).order_by(ExperimentAgentConfig.id)
            ).all()
        assert [(c.step_key, c.model_id) for c in configs] == [
            (str(world["agent"]), world["models"][0]),
            (f"{world['agent']}#2", world["models"][2]),
            (str(world["agent"]), world["models"][1]),
            (f"{world['agent']}#2", world["models"][2]),
        ]

    def test_the_experiment_knows_its_coordinates_by_step(self, client, world):
        body = client.post("/batches", json=self.twice(world)).json()

        coordinates = body["experiments"][1]["coordinates"]
        assert [(c["step_key"], c["value"]) for c in coordinates] == [
            (str(world["agent"]), world["models"][1]),
            (f"{world['agent']}#2", world["models"][2]),
        ]
        experiment = client.get(f"/experiments/{body['experiments'][1]['id']}").json()
        assert experiment["variant"] == {
            str(world["agent"]): {"model_id": world["models"][1]},
            f"{world['agent']}#2": {"model_id": world["models"][2]},
        }

    def test_varying_a_step_that_is_not_in_the_batch_is_refused(self, client, world):
        body = payload(world, [])
        body["variations"] = [
            {
                "step_key": f"{world['agent']}#2",
                "field": "model_id",
                "values": [world["models"][1]],
            }
        ]

        response = client.post("/batches", json=body)

        assert response.status_code == 422
        assert "not an active step" in response.json()["detail"]


class TestBaseRun:
    """The base configuration is one of the batch's runs."""

    def derived(self, world, engine, *, skip, models=(0, 1)):
        with scoped(engine) as s:
            base = Experiment(name="Base", dataset_id=world["dataset"])
            s.add(base)
            s.commit()
            base_id = base.id
        data = payload(world, [model_axis(world, *models)])
        data["base_experiment_id"] = base_id
        data["skip_base_point"] = skip
        return data

    def test_base_value_runs_like_any_other(self, client, world):
        # From scratch: models a (the base) and b are both run
        body = client.post(
            "/batches", json=payload(world, [model_axis(world, 0, 1)])
        ).json()

        assert [e["name"] for e in body["experiments"]] == [
            "Compare · m-a",
            "Compare · m-b",
        ]

    def test_existing_base_experiment_is_not_repeated(self, client, world, engine):
        data = self.derived(world, engine, skip=True)

        body = client.post("/batches", json=data).json()

        assert [e["name"] for e in body["experiments"]] == ["Compare · m-b"]

    def test_base_experiment_is_repeated_when_not_skipped(self, client, world, engine):
        data = self.derived(world, engine, skip=False)

        body = client.post("/batches", json=data).json()

        assert len(body["experiments"]) == 2

    def test_skip_needs_a_base_experiment(self, client, world):
        data = payload(world, [model_axis(world, 0, 1)])
        data["skip_base_point"] = True

        body = client.post("/batches", json=data).json()

        assert len(body["experiments"]) == 2

    def test_only_the_all_base_run_is_skipped_in_a_grid(self, client, world, engine):
        data = self.derived(world, engine, skip=True)
        data["variations"].append(
            {
                "agent_id": world["agent"],
                "field": "prompt_version_id",
                "values": [world["v1"], world["v2"]],
            }
        )

        body = client.post("/batches", json=data).json()

        assert [e["name"] for e in body["experiments"]] == [
            "Compare · m-a · Grader v2",
            "Compare · m-b · Grader v1",
            "Compare · m-b · Grader v2",
        ]

    def test_nothing_left_to_run_is_refused(self, client, world, engine, jobs):
        data = self.derived(world, engine, skip=True, models=(0,))

        response = client.post("/batches", json=data)

        assert response.status_code == 422
        assert jobs.started == []

    def test_model_default_temperature_is_a_value(self, client, world, engine):
        variations = [
            {
                "agent_id": world["agent"],
                "field": "temperature",
                "values": [None, 0.7],
            }
        ]
        body = client.post("/batches", json=payload(world, variations)).json()

        assert [e["name"] for e in body["experiments"]] == [
            "Compare · default T",
            "Compare · T=0.7",
        ]
        with scoped(engine) as s:
            configs = s.exec(
                select(ExperimentAgentConfig).order_by(ExperimentAgentConfig.id)
            ).all()
        assert [c.temperature for c in configs] == [None, 0.7]


class TestCreateBatchValidation:
    def assert_nothing_created(self, engine, jobs):
        with scoped(engine) as s:
            assert s.exec(select(Batch)).all() == []
            assert s.exec(select(Experiment)).all() == []
        assert jobs.started == []

    def test_prompt_with_unmapped_variable_is_refused(
        self, client, world, engine, jobs
    ):
        variations = [
            {
                "agent_id": world["agent"],
                "field": "prompt_version_id",
                "values": [world["v2"], world["v3"]],
            }
        ]
        response = client.post("/batches", json=payload(world, variations))

        assert response.status_code == 422
        assert "reference" in response.json()["detail"]
        self.assert_nothing_created(engine, jobs)

    def test_unknown_model_is_refused_without_creating_anything(
        self, client, world, engine, jobs
    ):
        variations = [
            {
                "agent_id": world["agent"],
                "field": "model_id",
                "values": [world["models"][0], 9999],
            }
        ]
        response = client.post("/batches", json=payload(world, variations))

        assert response.status_code == 422
        self.assert_nothing_created(engine, jobs)

    def test_varying_an_agent_outside_the_batch_is_refused(self, client, world):
        variations = [
            {"agent_id": 9999, "field": "model_id", "values": [world["models"][0]]}
        ]
        assert client.post("/batches", json=payload(world, variations)).status_code == 422

    def test_too_many_experiments_are_refused(self, client, world):
        variations = [
            {
                "agent_id": world["agent"],
                "field": "temperature",
                "values": [i / 10 for i in range(51)],
            }
        ]
        response = client.post("/batches", json=payload(world, variations))
        assert response.status_code == 422
        assert "51" in response.json()["detail"]

    def test_needs_a_variation(self, client, world):
        assert client.post("/batches", json=payload(world, [])).status_code == 422


class TestManageBatch:
    def create(self, client, world):
        return client.post(
            "/batches", json=payload(world, [model_axis(world, 0, 1)])
        ).json()

    def test_status_follows_the_experiments(self, client, world, engine):
        body = self.create(client, world)
        assert body["status"] == "pending"

        with scoped(engine) as s:
            for experiment in s.exec(select(Experiment)).all():
                experiment.status = "completed"
                s.add(experiment)
            s.commit()

        body = client.get(f"/batches/{body['id']}").json()
        assert body["status"] == "completed"
        assert body["counts"] == {"completed": 2}

    def test_cancel_stops_every_experiment(self, client, world, jobs):
        body = self.create(client, world)

        response = client.post(f"/batches/{body['id']}/cancel")

        assert response.json()["cancelled"] == 2
        assert sorted(jobs.cancelled) == sorted(e["id"] for e in body["experiments"])

    def test_rerun_starts_every_experiment_that_is_not_running(
        self, client, world, engine, jobs
    ):
        body = self.create(client, world)
        running, idle = body["experiments"][0]["id"], body["experiments"][1]["id"]
        jobs.started.clear()
        with scoped(engine) as s:
            for experiment_id, status in ((running, "running"), (idle, "completed")):
                experiment = s.get(Experiment, experiment_id)
                experiment.status = status
                s.add(experiment)
            s.commit()

        response = client.post(f"/batches/{body['id']}/rerun")

        assert response.json() == {"batch_id": body["id"], "started": 1, "skipped": 1}
        assert jobs.started == [idle]

    def test_rerun_schedules_the_runs_on_the_event_loop(
        self, client, world, engine, jobs, monkeypatch
    ):
        # `jobs` replaces start_experiment, which hides that the real one needs
        # a running loop: use it, with the run itself stubbed out
        async def no_run(experiment_id):
            return None

        monkeypatch.setattr(async_jobs, "start_experiment", REAL_START_EXPERIMENT)
        monkeypatch.setattr(async_jobs, "run_experiment_async", no_run)
        body = self.create(client, world)

        response = client.post(f"/batches/{body['id']}/rerun")

        assert response.json()["started"] == 2

    def test_rerun_of_an_unknown_batch_is_a_404(self, client):
        assert client.post("/batches/999/rerun").status_code == 404

    def test_deleting_a_batch_keeps_its_experiments(self, client, world, engine):
        body = self.create(client, world)

        assert client.delete(f"/batches/{body['id']}").status_code == 204

        assert client.get(f"/batches/{body['id']}").status_code == 404
        with scoped(engine) as s:
            experiments = s.exec(select(Experiment)).all()
        assert len(experiments) == 2
        assert all(e.batch_id is None for e in experiments)

    def test_deleting_the_base_experiment_keeps_the_batch(
        self, client, world, engine
    ):
        with scoped(engine) as s:
            base = Experiment(name="Base", dataset_id=world["dataset"])
            s.add(base)
            s.commit()
            base_id = base.id
        data = payload(world, [model_axis(world, 1)])
        data["base_experiment_id"] = base_id
        batch_id = client.post("/batches", json=data).json()["id"]

        client.delete(f"/experiments/{base_id}")

        batch = client.get(f"/batches/{batch_id}").json()
        assert batch["base_experiment_id"] is None


class TestExecutionFigures:
    """What the lists say about the executions of an experiment."""

    start = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)

    def create(self, client, world):
        return client.post(
            "/batches", json=payload(world, [model_axis(world, 0, 1)])
        ).json()

    def execute(
        self, engine, experiment_id, hours, seconds, status="completed", **figures
    ):
        """An execution that started `hours` after `start` and lasted `seconds`."""
        started = self.start + timedelta(hours=hours)
        with scoped(engine) as s:
            execution = ExperimentExecution(
                experiment_id=experiment_id,
                started_at=started,
                completed_at=started + timedelta(seconds=seconds),
                status=status,
                dataset_snapshot="{}",
                **figures,
            )
            s.add(execution)
            s.commit()
            return execution.id

    def test_experiment_without_execution_has_no_figures(self, client, world):
        body = self.create(client, world)

        experiment = client.get(f"/experiments/{body['experiments'][0]['id']}").json()

        assert experiment["execution_count"] == 0
        assert experiment["duration_seconds"] is None
        assert experiment["total_tokens"] is None

    def test_experiment_shows_its_latest_execution_and_counts_the_others(
        self, client, world, engine
    ):
        experiment_id = self.create(client, world)["experiments"][0]["id"]
        self.execute(engine, experiment_id, 0, 30, total_tokens=100, total_cost_usd=1)
        self.execute(
            engine,
            experiment_id,
            1,
            90,
            total_tokens=250,
            total_cost_usd=2.5,
            rows_failed=3,
        )

        experiment = client.get(f"/experiments/{experiment_id}").json()

        assert experiment["execution_count"] == 2
        assert experiment["duration_seconds"] == 90
        assert experiment["total_tokens"] == 250
        assert experiment["total_cost_usd"] == 2.5
        assert experiment["rows_failed"] == 3

    def test_experiment_list_carries_the_figures(self, client, world, engine):
        experiment_id = self.create(client, world)["experiments"][0]["id"]
        self.execute(engine, experiment_id, 0, 30, total_tokens=100)

        listed = {e["id"]: e for e in client.get("/experiments").json()}

        assert listed[experiment_id]["execution_count"] == 1
        assert listed[experiment_id]["total_tokens"] == 100

    def test_a_running_execution_has_no_duration_yet(self, client, world, engine):
        experiment_id = self.create(client, world)["experiments"][0]["id"]
        with scoped(engine) as s:
            s.add(
                ExperimentExecution(
                    experiment_id=experiment_id,
                    started_at=self.start,
                    status="running",
                    dataset_snapshot="{}",
                )
            )
            s.commit()

        experiment = client.get(f"/experiments/{experiment_id}").json()

        assert experiment["execution_count"] == 1
        assert experiment["duration_seconds"] is None

    def test_batch_experiments_carry_the_same_figures(self, client, world, engine):
        body = self.create(client, world)
        first = body["experiments"][0]["id"]
        self.execute(engine, first, 0, 30, total_tokens=100)
        self.execute(engine, first, 1, 60, total_tokens=300, rows_failed=2)

        experiments = {
            e["id"]: e for e in client.get(f"/batches/{body['id']}").json()["experiments"]
        }

        assert experiments[first]["execution_count"] == 2
        assert experiments[first]["duration_seconds"] == 60
        assert experiments[first]["total_tokens"] == 300
        assert experiments[first]["rows_failed"] == 2
        other = next(i for i in experiments if i != first)
        assert experiments[other]["execution_count"] == 0

    def test_batch_adds_up_its_experiments(self, client, world, engine):
        body = self.create(client, world)
        first, second = (e["id"] for e in body["experiments"])
        self.execute(engine, first, 0, 30, total_tokens=100, total_cost_usd=1)
        # Replaced by the next execution: only counted
        self.execute(engine, second, 0, 30, total_tokens=999, total_cost_usd=9)
        self.execute(engine, second, 1, 30, total_tokens=200, total_cost_usd=0.5)

        batch = client.get(f"/batches/{body['id']}").json()

        assert batch["execution_count"] == 3
        assert batch["total_tokens"] == 300
        assert batch["total_cost_usd"] == 1.5

    def test_batch_without_execution_has_no_totals(self, client, world):
        batch = client.get(f"/batches/{self.create(client, world)['id']}").json()

        assert batch["execution_count"] == 0
        assert batch["total_tokens"] is None
        assert batch["total_cost_usd"] is None


    def test_batch_experiment_points_at_its_latest_completed_execution(
        self, client, world, engine
    ):
        body = self.create(client, world)
        first, second, *_ = (e["id"] for e in body["experiments"])
        self.execute(engine, first, 0, 30)
        completed = self.execute(engine, first, 1, 30)
        self.execute(engine, first, 2, 30, status="failed")
        self.execute(engine, second, 0, 30, status="failed")

        experiments = {
            e["id"]: e for e in client.get(f"/batches/{body['id']}").json()["experiments"]
        }

        assert experiments[first]["execution_status"] == "failed"
        assert experiments[first]["last_completed_execution_id"] == completed
        assert experiments[second]["last_completed_execution_id"] is None


class TestCreateWithSeed:
    def create(self, client, world, **fields):
        return client.post(
            "/experiments",
            json={
                "name": "Solo",
                "dataset_id": world["dataset"],
                "agent_configurations": {
                    str(world["agent"]): {
                        "is_active": True,
                        "prompt_version_id": world["v1"],
                        "model_id": world["models"][0],
                        "input_mappings": [
                            {"variable": "answer", "source": "dataset", "sourceColumn": "text"}
                        ],
                    }
                },
                **fields,
            },
        )

    def test_random_sample_takes_the_seed_it_is_given(self, client, world):
        response = self.create(
            client, world, sampling_type="random", sampling_size=5, sampling_seed=7
        )

        assert response.status_code in (200, 201)
        assert response.json()["sampling_seed"] == 7

    def test_random_sample_draws_a_seed_when_none_is_given(self, client, world):
        body = self.create(
            client, world, sampling_type="random", sampling_size=5
        ).json()

        assert body["sampling_seed"] is not None

    def test_seed_is_ignored_when_the_sample_is_not_random(self, client, world):
        body = self.create(
            client, world, sampling_type="all", sampling_seed=7
        ).json()

        assert body["sampling_seed"] is None


class TestResample:
    def experiment(self, world, engine, **fields):
        with scoped(engine) as s:
            experiment = Experiment(
                name="Solo", dataset_id=world["dataset"], **fields
            )
            s.add(experiment)
            s.commit()
            return experiment.id

    def test_draws_a_new_seed(self, client, world, engine):
        exp_id = self.experiment(
            world, engine, sampling_type="random", sampling_size=5, sampling_seed=1
        )

        body = client.post(f"/experiments/{exp_id}/resample").json()

        assert body["sampling_seed"] not in (None, 1)
        assert client.get(f"/experiments/{exp_id}").json()["sampling_seed"] == body["sampling_seed"]

    def test_only_a_random_sample_can_be_redrawn(self, client, world, engine):
        exp_id = self.experiment(world, engine, sampling_type="all")

        assert client.post(f"/experiments/{exp_id}/resample").status_code == 400

    def test_the_sample_of_a_batch_is_not_redrawn_from_one_experiment(
        self, client, world
    ):
        data = payload(world, [model_axis(world, 0, 1)])
        data["config"].update(sampling_type="random", sampling_size=5)
        body = client.post("/batches", json=data).json()
        exp_id = body["experiments"][0]["id"]

        assert client.post(f"/experiments/{exp_id}/resample").status_code == 409
        # The experiment shows the batch's seed
        assert client.get(f"/experiments/{exp_id}").json()["sampling_seed"] is not None


@pytest.fixture
def other_dataset(engine, world, datasets_dir):
    """The world's dataset on disk, and a second one with other column names."""
    (datasets_dir / "answers.csv").write_text("text,label\na,1\nb,0\nc,1\n")
    (datasets_dir / "other.csv").write_text("content,gold\nx,1\ny,0\n")
    with scoped(engine) as s:
        other = Dataset(name="other", file_path="other.csv")
        s.add(other)
        s.commit()
        return other.id


def dataset_axis(world, other, column_maps=None):
    return {
        "field": "dataset_id",
        "values": [world["dataset"], other],
        "column_maps": column_maps,
    }


class TestDatasetAxis:
    def test_one_experiment_per_dataset_and_value(
        self, client, world, other_dataset, engine
    ):
        variations = [
            model_axis(world, 0, 1),
            dataset_axis(world, other_dataset, {str(other_dataset): {"text": "content"}}),
        ]
        response = client.post("/batches", json=payload(world, variations))

        assert response.status_code == 201
        body = response.json()
        # The dataset leads the names, and varies slowest
        assert [e["name"] for e in body["experiments"]] == [
            "Compare · answers · m-a",
            "Compare · answers · m-b",
            "Compare · other · m-a",
            "Compare · other · m-b",
        ]
        assert body["dataset_id"] is None
        assert body["dataset_name"] == "answers, other"
        axis = body["variations"][0]
        assert (axis["step_key"], axis["agent_id"], axis["agent_name"]) == (
            "dataset",
            None,
            "Dataset",
        )
        assert [v["column_map"] for v in axis["values"]] == [None, {"text": "content"}]

        with scoped(engine) as s:
            created = s.exec(select(Experiment).order_by(Experiment.id)).all()
        assert [e.dataset_id for e in created] == [world["dataset"]] * 2 + [other_dataset] * 2
        assert [json.loads(e.column_map) if e.column_map else None for e in created] == [
            None,
            None,
            {"text": "content"},
            {"text": "content"},
        ]

    def test_dataset_alone_is_a_batch(self, client, world, other_dataset):
        response = client.post(
            "/batches",
            json=payload(
                world,
                [dataset_axis(world, other_dataset, {str(other_dataset): {"text": "content"}})],
            ),
        )
        assert response.status_code == 201
        assert [e["name"] for e in response.json()["experiments"]] == [
            "Compare · answers",
            "Compare · other",
        ]

    def test_a_column_the_agents_read_must_have_a_counterpart(
        self, client, world, other_dataset, jobs
    ):
        response = client.post(
            "/batches", json=payload(world, [dataset_axis(world, other_dataset)])
        )
        assert response.status_code == 422
        assert "no column for text" in response.json()["detail"]
        assert jobs.started == []

    def test_unmapped_agents_need_their_prompt_variables(
        self, client, world, other_dataset, datasets_dir
    ):
        (datasets_dir / "answers.csv").write_text("answer,label\na,1\n")
        response = client.post(
            "/batches",
            json=payload(world, [dataset_axis(world, other_dataset)], input_mappings=[]),
        )
        assert response.status_code == 422
        assert "no column for answer" in response.json()["detail"]

    def test_a_column_read_under_another_name_is_gone_under_its_own(
        self, client, world, other_dataset, datasets_dir
    ):
        # "content" stands for "text", while the agents read "content" too
        (datasets_dir / "answers.csv").write_text("text,content,label\na,b,1\n")
        world_mappings = [
            {"variable": "answer", "source": "dataset", "sourceColumn": "text"},
            {"variable": "content", "source": "dataset", "sourceColumn": "content"},
        ]
        response = client.post(
            "/batches",
            json=payload(
                world,
                [dataset_axis(world, other_dataset, {str(other_dataset): {"text": "content"}})],
                input_mappings=world_mappings,
            ),
        )
        assert response.status_code == 422
        assert "no column for content" in response.json()["detail"]

    def test_a_copied_experiment_keeps_its_column_map(
        self, client, world, other_dataset, engine
    ):
        config = payload(world, [])["config"]
        response = client.post(
            "/experiments",
            json={
                "name": "Copy",
                **config,
                "dataset_id": other_dataset,
                "column_map": {"text": "content"},
            },
        )
        assert response.status_code == 201
        assert response.json()["column_map"] == {"text": "content"}

    def test_a_copied_column_map_must_name_columns_of_the_dataset(
        self, client, world, other_dataset
    ):
        config = payload(world, [])["config"]
        response = client.post(
            "/experiments",
            json={
                **config,
                "name": "Copy",
                "dataset_id": other_dataset,
                "column_map": {"text": "nope"},
            },
        )
        assert response.status_code == 422
        assert "has no column nope" in response.json()["detail"]

    def test_the_base_point_of_a_batch_keeps_a_copied_column_map(
        self, client, world, other_dataset, engine
    ):
        body = payload(world, [model_axis(world, 0, 1)])
        body["config"].update(dataset_id=other_dataset, column_map={"text": "content"})
        response = client.post("/batches", json=body)
        assert response.status_code == 201
        with scoped(engine) as s:
            created = s.exec(select(Experiment).order_by(Experiment.id)).all()
        assert [json.loads(e.column_map) for e in created] == [{"text": "content"}] * 2

    def test_a_copied_column_map_cannot_vary_the_dataset(
        self, client, world, other_dataset
    ):
        body = payload(world, [dataset_axis(world, other_dataset)])
        body["config"]["column_map"] = {"text": "text"}
        response = client.post("/batches", json=body)
        assert response.status_code == 422
        assert "cannot be varied" in response.json()["detail"]

    def test_unknown_base_dataset_is_refused(self, client, world, other_dataset):
        body = payload(world, [dataset_axis(world, other_dataset)])
        body["config"]["dataset_id"] = 999_999
        response = client.post("/batches", json=body)
        assert response.status_code == 422
        assert "999999 not found" in response.json()["detail"]

    def test_mapped_columns_must_exist(self, client, world, other_dataset):
        response = client.post(
            "/batches",
            json=payload(
                world,
                [dataset_axis(world, other_dataset, {str(other_dataset): {"text": "nope"}})],
            ),
        )
        assert response.status_code == 422
        assert "has no column nope" in response.json()["detail"]

    def test_a_range_past_the_end_of_a_dataset_is_refused(
        self, client, world, other_dataset
    ):
        body = payload(
            world,
            [dataset_axis(world, other_dataset, {str(other_dataset): {"text": "content"}})],
        )
        body["config"].update(
            sampling_type="range", sampling_start_row=3, sampling_end_row=3
        )
        response = client.post("/batches", json=body)
        assert response.status_code == 422
        assert "'other' has 2 rows" in response.json()["detail"]

    def test_the_execution_reads_the_rows_under_the_base_names(
        self, client, world, other_dataset, engine
    ):
        body = client.post(
            "/batches",
            json=payload(
                world,
                [dataset_axis(world, other_dataset, {str(other_dataset): {"text": "content"}})],
            ),
        ).json()
        with scoped(engine) as s:
            snapshot = json.loads(
                create_execution_snapshot(body["experiments"][1]["id"], s).dataset_snapshot
            )
        assert snapshot["file_path"] == "other.csv"
        assert snapshot["column_map"] == {"text": "content"}
        assert snapshot["dataset_axis_batch_id"] == body["id"]
