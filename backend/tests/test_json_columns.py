"""JSON documents are stored as jsonb, and handled as text by the application."""

import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import StatementError
from sqlmodel import select

from api import prompts
from tables import Analysis, Prompt, PromptVersion
from tests.conftest import api_client, scoped


@pytest.fixture
def version(engine):
    with scoped(engine) as s:
        prompt = Prompt(name="p")
        s.add(prompt)
        s.flush()
        s.add(PromptVersion(prompt_id=prompt.id, version="1", variables='["a", "é"]'))
        s.commit()
        return prompt.id


def test_a_document_is_stored_as_jsonb_and_comes_back_as_equivalent_text(
    engine, version
):
    with scoped(engine) as s:
        stored = s.exec(select(PromptVersion)).one().variables
        kind = (
            s.connection()
            .execute(text("SELECT jsonb_typeof(variables) FROM promptversion"))
            .scalar()
        )

    assert kind == "array"
    assert isinstance(stored, str)
    assert json.loads(stored) == ["a", "é"]
    assert "é" in stored


def test_a_missing_document_is_null_not_a_json_null(engine):
    with scoped(engine) as s:
        prompt = Prompt(name="p")
        s.add(prompt)
        s.flush()
        s.add(PromptVersion(prompt_id=prompt.id, version="1"))
        s.commit()

    with scoped(engine) as s:
        assert s.exec(select(PromptVersion)).one().variables is None
        assert (
            s.connection()
            .execute(text("SELECT variables IS NULL FROM promptversion"))
            .scalar()
        )


def test_a_text_that_is_not_json_is_refused(engine):
    with scoped(engine) as s:
        s.add(Analysis(name="a", config="not json", runs="[]"))
        with pytest.raises(StatementError):
            s.commit()


def test_a_json_string_value_comes_back_as_such(engine):
    with scoped(engine) as s:
        s.add(Analysis(name="a", config='"just text"', runs="[]"))
        s.commit()

    with scoped(engine) as s:
        assert json.loads(s.exec(select(Analysis)).one().config) == "just text"


@pytest.fixture
def client(engine):
    return api_client(engine, prompts)


@pytest.fixture
def prompt_id(engine):
    with scoped(engine) as s:
        prompt = Prompt(name="p")
        s.add(prompt)
        s.commit()
        return prompt.id


def create_version(client, prompt_id, variables):
    return client.post(
        f"/prompts/{prompt_id}/versions",
        json={"version": "1", "variables": variables},
    )


def test_variables_that_are_not_json_are_a_422(client, prompt_id):
    assert create_version(client, prompt_id, "not json").status_code == 422


def test_variables_are_returned_as_the_text_that_was_sent(client, prompt_id):
    response = create_version(client, prompt_id, '["name", "text"]')

    assert response.status_code == 201
    assert json.loads(response.json()["variables"]) == ["name", "text"]


@pytest.mark.parametrize("blank", ["", "  "])
def test_blank_variables_mean_none(client, prompt_id, blank):
    response = create_version(client, prompt_id, blank)

    assert response.status_code == 201
    assert response.json()["variables"] is None


def test_updating_with_variables_that_are_not_json_is_a_422(client, prompt_id):
    version_id = create_version(client, prompt_id, "[]").json()["id"]

    response = client.put(f"/prompt-versions/{version_id}", json={"variables": "{"})

    assert response.status_code == 422
