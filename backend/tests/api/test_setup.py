import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

import credentials
from api import setup
from db import get_session
from tables import Agent, AgentTeam, Dataset, Experiment, Model, Prompt, PromptVersion
from tests.conftest import TEST_WORKSPACE_ID, scoped
from workspace_scope import scope_session


@pytest.fixture
def client(engine, monkeypatch):
    # No key on the machine running the tests
    monkeypatch.setattr(credentials, "instance_provides", lambda provider: False)
    app = FastAPI()
    app.include_router(setup.router)

    def _session():
        with Session(engine) as session:
            scope_session(session, TEST_WORKSPACE_ID)
            yield session

    app.dependency_overrides[get_session] = _session
    return TestClient(app)


def progress(client) -> dict[str, bool]:
    response = client.get("/setup")
    assert response.status_code == 200
    return response.json()


def test_an_empty_workspace_has_taken_no_step(client):
    assert progress(client) == {
        "provider": False,
        "dataset": False,
        "prompt": False,
        "model": False,
        "agent": False,
        "experiment": False,
    }


def test_each_step_is_ticked_by_what_the_workspace_holds(client, engine):
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        team = AgentTeam(name="Graders")
        model = Model(name="m", provider="openai")
        prompt = Prompt(name="Grader")
        s.add_all([dataset, team, model, prompt])
        s.flush()
        s.add(PromptVersion(prompt_id=prompt.id, version="1"))
        s.add(Agent(name="a", team_id=team.id))
        s.commit()

    assert progress(client) == {
        "provider": False,
        "dataset": True,
        # The prompt counts once it has a version
        "prompt": True,
        "model": True,
        "agent": True,
        "experiment": False,
    }

    with scoped(engine) as s:
        s.add(Experiment(name="run", dataset_id=1))
        s.commit()
    assert progress(client)["experiment"] is True


def test_a_prompt_without_a_version_is_not_a_step_done(client, engine):
    with scoped(engine) as s:
        s.add(Prompt(name="Grader"))
        s.commit()

    assert progress(client)["prompt"] is False


def test_a_key_of_the_instance_counts_as_a_provider(client, monkeypatch):
    monkeypatch.setattr(credentials, "instance_provides", lambda provider: provider == "openai")

    assert progress(client)["provider"] is True
