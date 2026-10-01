import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

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
    Model,
    Prompt,
    PromptVersion,
)


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
def jobs(monkeypatch):
    """Experiments handed to the background runner, instead of running."""
    jobs = SimpleNamespace(started=[], cancelled=[])
    monkeypatch.setattr(async_jobs, "start_experiment", jobs.started.append)
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
            yield session

    app.dependency_overrides[get_session] = _session
    return TestClient(app)


@pytest.fixture
def world(engine):
    """A dataset, an agent with two prompt versions and three models."""
    with Session(engine) as s:
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

        with Session(engine) as s:
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

        with Session(engine) as s:
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
        with Session(engine) as s:
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

        with Session(engine) as s:
            assert s.get(Batch, batch_id).sampling_seed is not None

    def test_no_seed_when_the_sample_is_not_random(self, client, world, engine):
        batch_id = client.post(
            "/batches", json=payload(world, [model_axis(world, 0, 1)])
        ).json()["id"]

        with Session(engine) as s:
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
        with Session(engine) as s:
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
        with Session(engine) as s:
            configs = s.exec(
                select(ExperimentAgentConfig).order_by(ExperimentAgentConfig.id)
            ).all()
        assert [c.temperature for c in configs] == [None, 0.7]


class TestCreateBatchValidation:
    def assert_nothing_created(self, engine, jobs):
        with Session(engine) as s:
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

        with Session(engine) as s:
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

    def test_deleting_a_batch_keeps_its_experiments(self, client, world, engine):
        body = self.create(client, world)

        assert client.delete(f"/batches/{body['id']}").status_code == 200

        assert client.get(f"/batches/{body['id']}").status_code == 404
        with Session(engine) as s:
            experiments = s.exec(select(Experiment)).all()
        assert len(experiments) == 2
        assert all(e.batch_id is None for e in experiments)

    def test_deleting_the_base_experiment_keeps_the_batch(
        self, client, world, engine
    ):
        with Session(engine) as s:
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
