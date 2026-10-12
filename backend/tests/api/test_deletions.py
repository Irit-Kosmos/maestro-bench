"""What deleting an item does to the rows that still point to it."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from api import agents, datasets, models, prompts
from db import get_session
from tables import (
    Agent,
    Dataset,
    Experiment,
    ExperimentAgentConfig,
    Model,
    Prompt,
    PromptVersion,
)
from tests.conftest import TEST_WORKSPACE_ID, scoped
from workspace_scope import scope_session


@pytest.fixture
def client(engine):
    app = FastAPI()
    for module in (agents, datasets, models, prompts):
        app.include_router(module.router)

    def _session():
        with Session(engine) as session:
            scope_session(session, TEST_WORKSPACE_ID)
            yield session

    app.dependency_overrides[get_session] = _session
    return TestClient(app)


@pytest.fixture
def world(engine):
    """An experiment whose single agent config uses a model and a prompt version."""
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        prompt = Prompt(name="Grader")
        model = Model(name="m-a", provider="openai")
        s.add_all([dataset, prompt, model])
        s.flush()
        version = PromptVersion(prompt_id=prompt.id, version="1")
        s.add(version)
        s.flush()
        agent = Agent(
            name="Grader",
            default_model_id=model.id,
            default_prompt_version_id=version.id,
        )
        experiment = Experiment(name="Run", dataset_id=dataset.id)
        s.add_all([agent, experiment])
        s.flush()
        config = ExperimentAgentConfig(
            experiment_id=experiment.id,
            agent_id=agent.id,
            model_id=model.id,
            prompt_version_id=version.id,
        )
        s.add(config)
        s.commit()
        return {
            "dataset": dataset.id,
            "agent": agent.id,
            "model": model.id,
            "version": version.id,
            "config": config.id,
        }


def test_deleting_a_model_empties_the_references_to_it(client, engine, world):
    assert client.delete(f"/models/{world['model']}").status_code == 204

    with scoped(engine) as s:
        assert s.get(Agent, world["agent"]).default_model_id is None
        config = s.get(ExperimentAgentConfig, world["config"])
        assert config.model_id is None
        assert config.prompt_version_id == world["version"]


def test_deleting_a_prompt_version_empties_the_references_to_it(
    client, engine, world
):
    assert client.delete(f"/prompt-versions/{world['version']}").status_code == 204

    with scoped(engine) as s:
        assert s.get(Agent, world["agent"]).default_prompt_version_id is None
        config = s.get(ExperimentAgentConfig, world["config"])
        assert config.prompt_version_id is None
        assert config.model_id == world["model"]


def test_an_agent_used_by_an_experiment_cannot_be_deleted(client, engine, world):
    response = client.delete(f"/agents/{world['agent']}")

    assert response.status_code == 409
    assert "1 experiment" in response.json()["detail"]
    with scoped(engine) as s:
        assert s.get(Agent, world["agent"]) is not None


def test_an_unused_agent_can_be_deleted(client, engine, world):
    with scoped(engine) as s:
        s.delete(s.get(ExperimentAgentConfig, world["config"]))
        s.commit()

    assert client.delete(f"/agents/{world['agent']}").status_code == 204

    with scoped(engine) as s:
        assert s.get(Agent, world["agent"]) is None


def test_a_dataset_used_by_an_experiment_is_kept_with_its_file(
    client, engine, world, datasets_dir
):
    file = datasets_dir / "answers.csv"
    file.write_text("text\nhello\n")

    response = client.delete(f"/datasets/{world['dataset']}")

    assert response.status_code == 409
    assert file.is_file()
    with scoped(engine) as s:
        assert s.get(Dataset, world["dataset"]) is not None


def test_an_unused_dataset_is_deleted_with_its_file(client, engine, datasets_dir):
    file = datasets_dir / "spare.csv"
    file.write_text("text\nhello\n")
    with scoped(engine) as s:
        dataset = Dataset(name="spare", file_path="spare.csv")
        s.add(dataset)
        s.commit()
        dataset_id = dataset.id

    assert client.delete(f"/datasets/{dataset_id}").status_code == 204

    assert not file.exists()
    with scoped(engine) as s:
        assert s.get(Dataset, dataset_id) is None
