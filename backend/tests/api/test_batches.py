import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, select

import async_jobs
from api import batches, experiments
from db import get_session
from tables import (
    Agent,
    AgentTeam,
    Batch,
    Dataset,
    Experiment,
    ExperimentAgentConfig,
    ExperimentExecution,
    Model,
    Prompt,
    PromptVersion,
)
from tests.conftest import TEST_WORKSPACE_ID, scoped
from workspace_scope import scope_session

REAL_START_EXPERIMENT = async_jobs.start_experiment


@pytest.fixture
def jobs(monkeypatch):
    """Experiments handed to the background runner, instead of running."""
    jobs = SimpleNamespace(started=[], cancelled=[])
    monkeypatch.setattr(
        async_jobs,
        "start_experiment",
        lambda eid, workspace_id: jobs.started.append(eid) or "started",
    )
    monkeypatch.setattr(
        async_jobs, "cancel_experiment", lambda eid: jobs.cancelled.append(eid) or True
    )
    return jobs


@pytest.fixture
def client(engine, jobs):
    app = FastAPI()
    app.include_router(batches.router)
    app.include_router(experiments.router)

    def _session():
        with Session(engine) as session:
            scope_session(session, TEST_WORKSPACE_ID)
            yield session

    app.dependency_overrides[get_session] = _session
    return TestClient(app)


@pytest.fixture
def world(engine):
    """A dataset, an agent with two prompt versions and three models."""
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        team = AgentTeam(name="Graders")
        prompt = Prompt(name="Grader")
        s.add_all([dataset, team, prompt])
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
            team_id=team.id,
            default_prompt_version_id=v1.id,
            default_model_id=models[0].id,
        )
        s.add(agent)
        s.commit()
        return {
            "dataset": dataset.id,
            "team": team.id,
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
            "agent_teams": [str(world["team"])],
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

        assert client.delete(f"/batches/{body['id']}").status_code == 200

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
