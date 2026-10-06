import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import prompts


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(prompts.router)
    return TestClient(app)


def render(client, **body):
    return client.post("/prompts/render", json=body)


def test_renders_both_prompts_with_the_values(client):
    response = render(
        client,
        system_prompt="You grade {{ topic }}.",
        user_prompt="Answer: {{ answer }}",
        variables={"topic": "French", "answer": "Bonjour"},
    )
    assert response.status_code == 200
    assert response.json() == {"system": "You grade French.", "user": "Answer: Bonjour"}


def test_renders_the_legacy_slots_like_a_run_does(client):
    response = render(
        client,
        user_prompt="<answer></answer>",
        variables={"answer": "Bonjour"},
    )
    assert response.json()["user"] == "<answer>Bonjour</answer>"


def test_a_missing_variable_renders_empty_and_a_missing_prompt_is_empty(client):
    response = render(client, user_prompt="[{{ nope }}]")
    assert response.json() == {"system": "", "user": "[]"}


def test_a_template_reaching_for_the_interpreter_is_refused(client):
    response = render(
        client,
        user_prompt="{{ ''.__class__.__mro__[1].__subclasses__() }}",
    )
    assert response.status_code == 422
