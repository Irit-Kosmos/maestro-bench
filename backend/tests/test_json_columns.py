"""JSON documents are stored as jsonb, and handled as text by the application."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import StatementError
from sqlmodel import Session, SQLModel, select

import tables
from api import prompts
from db import get_session
from tables import Analysis, Dataset, Prompt, PromptVersion
from tests.conftest import TEST_WORKSPACE_ID, scoped
from workspace_scope import scope_session


def json_columns():
    return [
        (table.name, column.name)
        for table in SQLModel.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, tables.JsonText)
    ]


def test_the_json_columns_are_the_ones_expected():
    assert sorted(json_columns()) == [
        ("agentexecutionsnapshot", "final_formulas"),
        ("agentexecutionsnapshot", "final_input_mappings"),
        ("agentexecutionsnapshot", "final_variables"),
        ("analysis", "config"),
        ("analysis", "runs"),
        ("batch", "variations"),
        ("experimentagentconfig", "formulas"),
        ("experimentagentconfig", "input_mappings"),
        ("experimentexecution", "dataset_snapshot"),
        ("promptversion", "variables"),
    ]


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
        kind = s.execute(
            text("SELECT jsonb_typeof(variables) FROM promptversion")
        ).scalar()

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
        assert s.execute(text("SELECT variables IS NULL FROM promptversion")).scalar()


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
    app = FastAPI()
    app.include_router(prompts.router)

    def _session():
        with Session(engine) as session:
            scope_session(session, TEST_WORKSPACE_ID)
            yield session

    app.dependency_overrides[get_session] = _session
    return TestClient(app)


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


def test_a_dataset_is_untouched(engine):
    # Only the declared columns are JSON: a plain text column keeps any text
    with scoped(engine) as s:
        s.add(Dataset(name="not json", description="{", file_path="d.csv"))
        s.commit()
