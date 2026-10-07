import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from api import datasets
from db import get_session
from tables import Dataset
from tests.conftest import TEST_WORKSPACE_ID, scoped
from workspace_scope import scope_session


@pytest.fixture
def client(engine, data_dir):
    app = FastAPI()
    app.include_router(datasets.router)

    def _session():
        with Session(engine) as session:
            scope_session(session, TEST_WORKSPACE_ID)
            yield session

    app.dependency_overrides[get_session] = _session
    return TestClient(app)


@pytest.fixture
def dataset_id(engine):
    with scoped(engine) as s:
        dataset = Dataset(name="Answers", description="First batch", file_path="a.csv")
        s.add(dataset)
        s.commit()
        s.refresh(dataset)
        return dataset.id


def test_a_dataset_is_renamed_and_described(client, dataset_id, engine):
    response = client.put(
        f"/datasets/{dataset_id}", json={"name": " Questions ", "description": " Second "}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Questions"
    assert response.json()["description"] == "Second"
    with scoped(engine) as s:
        stored = s.get(Dataset, dataset_id)
        assert (stored.name, stored.description) == ("Questions", "Second")
        assert stored.file_path == "a.csv"


def test_what_is_not_sent_is_left_as_it_is(client, dataset_id):
    renamed = client.put(f"/datasets/{dataset_id}", json={"name": "Questions"}).json()
    assert renamed["description"] == "First batch"

    described = client.put(f"/datasets/{dataset_id}", json={"description": "Other"}).json()
    assert described["name"] == "Questions"


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_an_empty_description_clears_it(client, dataset_id, empty):
    response = client.put(f"/datasets/{dataset_id}", json={"description": empty})

    assert response.status_code == 200
    assert response.json()["description"] is None


@pytest.mark.parametrize("name", ["", "   "])
def test_a_dataset_keeps_a_name(client, dataset_id, engine, name):
    response = client.put(f"/datasets/{dataset_id}", json={"name": name})

    assert response.status_code == 422
    with scoped(engine) as s:
        assert s.get(Dataset, dataset_id).name == "Answers"


def test_the_file_cannot_be_swapped_through_an_update(client, dataset_id, engine):
    client.put(f"/datasets/{dataset_id}", json={"file_path": "../secret.csv"})

    with scoped(engine) as s:
        assert s.get(Dataset, dataset_id).file_path == "a.csv"


def test_an_unknown_dataset_is_not_found(client):
    assert client.put("/datasets/999", json={"name": "x"}).status_code == 404
