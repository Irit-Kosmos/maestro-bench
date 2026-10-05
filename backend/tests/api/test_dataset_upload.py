import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, select

import config
import workspace_files
from api import datasets
from db import get_session
from tables import Dataset
from tests.conftest import TEST_WORKSPACE_ID, scoped
from workspace_scope import scope_session

CSV = "id,text\n1,hello\n2,world\n"


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


def upload(client, body, filename="answers.csv", **params):
    return client.post(
        "/datasets/upload", params={"filename": filename, **params}, content=body
    )


def stored_files(workspace_id=TEST_WORKSPACE_ID):
    folder = workspace_files.datasets_dir(workspace_id)
    return sorted(folder.iterdir()) if folder.exists() else []


def test_an_uploaded_csv_becomes_a_dataset_in_the_workspace_folder(client, engine):
    response = upload(client, CSV, name="Answers", description="First batch")

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Answers"
    assert body["description"] == "First batch"
    (file,) = stored_files()
    assert body["file_path"] == file.name
    assert file.read_text() == CSV
    with scoped(engine) as s:
        assert s.exec(select(Dataset)).one().file_path == file.name


def test_the_stored_name_is_made_up_by_the_server(client):
    upload(client, CSV, filename="../../etc/passwd.csv")

    (file,) = stored_files()
    assert workspace_files.GENERATED_NAME.match(file.name)
    assert file.parent == workspace_files.datasets_dir(TEST_WORKSPACE_ID)


def test_the_name_defaults_to_the_file_name(client):
    assert upload(client, CSV, filename="mohler.csv").json()["name"] == "mohler"


def test_a_json_list_of_objects_is_accepted(client):
    rows = json.dumps([{"a": 1}, {"a": 2}])

    response = upload(client, rows, filename="rows.json")

    assert response.status_code == 201
    assert response.json()["file_path"].endswith(".json")


@pytest.mark.parametrize(
    ("filename", "body", "message"),
    [
        ("data.xlsx", CSV, "Only .csv and .json"),
        ("data", CSV, "Only .csv and .json"),
        ("data.csv", "", "empty"),
        ("data.csv", "id,text\n", "no rows"),
        ("data.csv", "id,id\n1,2\n", "duplicate"),
        ("data.csv", "id,text\n1,2,3\n", "more values"),
        ("data.csv", b"\xff\xfe\x00bad", "not a valid"),
        ("data.json", "{not json", "not a valid"),
        ("data.json", '{"a": 1}', "single object"),
        ("data.json", "[]", "no columns"),
        ("data.json", "[1, 2]", "list of objects"),
    ],
)
def test_a_file_that_cannot_be_a_dataset_is_refused_and_not_kept(
    client, engine, filename, body, message
):
    response = upload(client, body, filename=filename)

    assert response.status_code == 400
    assert message in response.json()["detail"]
    assert stored_files() == []
    with scoped(engine) as s:
        assert s.exec(select(Dataset)).all() == []


def test_a_file_over_the_limit_is_refused_and_not_kept(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_MB", 1)
    body = "id,text\n" + "1,xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n" * 40_000

    response = upload(client, body)

    assert response.status_code == 413
    assert stored_files() == []


def test_the_limit_applies_even_when_the_size_is_not_declared(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_MB", 1)
    chunks = (b"1,xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n" for _ in range(40_000))

    response = upload(client, chunks)

    assert response.status_code == 413
    assert stored_files() == []


def test_two_uploads_never_share_a_file(client):
    first = upload(client, CSV).json()["file_path"]
    second = upload(client, CSV).json()["file_path"]

    assert first != second
    assert len(stored_files()) == 2


def test_the_preview_of_a_csv_with_empty_cells_lists_its_columns(client):
    dataset_id = upload(client, "id,text\n1,\n2,\"two\nlines\"\n").json()["id"]

    response = client.get(f"/datasets/{dataset_id}/preview")

    assert response.status_code == 200
    body = response.json()
    assert body["headers"] == ["id", "text"]
    assert body["total_rows"] == 2
    assert body["sample_data"] == [
        {"id": "1", "text": ""},
        {"id": "2", "text": "two\nlines"},
    ]


def test_a_dataset_cannot_point_into_another_workspace(client, engine, data_dir):
    other = workspace_files.datasets_dir(2)
    other.mkdir(parents=True)
    (other / "secret.csv").write_text(CSV)

    created = client.post(
        "/datasets", json={"name": "x", "file_path": "../2/datasets/secret.csv"}
    )
    assert created.status_code == 400

    # Even a row that got there another way reads nothing outside its folder
    with scoped(engine) as s:
        dataset = Dataset(name="x", file_path="../../2/datasets/secret.csv")
        s.add(dataset)
        s.commit()
        dataset_id = dataset.id
    assert client.get(f"/datasets/{dataset_id}/preview").status_code == 400
    assert client.get(f"/datasets/{dataset_id}/rows").status_code == 400


def test_deleting_a_dataset_only_removes_the_file_of_its_workspace(client, data_dir):
    other = workspace_files.datasets_dir(2)
    other.mkdir(parents=True)
    (other / "same.csv").write_text(CSV)
    created = upload(client, CSV).json()

    assert client.delete(f"/datasets/{created['id']}").status_code == 204

    assert stored_files() == []
    assert (other / "same.csv").exists()
