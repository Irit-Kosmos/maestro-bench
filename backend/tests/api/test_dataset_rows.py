import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

import dataset_rows
import dataset_utils
from api import datasets
from db import get_session
from tables import Dataset


@pytest.fixture
def datasets_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(dataset_utils, "get_datasets_dir", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def client(engine, datasets_dir):
    app = FastAPI()
    app.include_router(datasets.router)

    def _session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _session
    return TestClient(app)


def _add_dataset(engine, file_path: str) -> int:
    with Session(engine) as s:
        dataset = Dataset(name="d", file_path=file_path)
        s.add(dataset)
        s.commit()
        s.refresh(dataset)
        return dataset.id


def test_csv_round_trip_keeps_cells_as_written(client, engine, datasets_dir):
    (datasets_dir / "a.csv").write_text(
        'id,text\n1.10,"line one\nline two"\n2.0,plain\n', encoding="utf-8"
    )
    dataset_id = _add_dataset(engine, "a.csv")

    body = client.get(f"/datasets/{dataset_id}/rows").json()
    assert body["headers"] == ["id", "text"]
    assert body["total_rows"] == 2
    assert body["rows"][0] == {"id": "1.10", "text": "line one\nline two"}
    assert body["read_only_reason"] is None

    body["rows"][1]["text"] = "edited"
    saved = client.put(
        f"/datasets/{dataset_id}/rows",
        json={"rows": body["rows"], "revision": body["revision"]},
    )
    assert saved.status_code == 200

    reread = client.get(f"/datasets/{dataset_id}/rows").json()
    assert reread["rows"] == body["rows"]
    assert reread["revision"] == saved.json()["revision"]
    assert "1.10," in (datasets_dir / "a.csv").read_text(encoding="utf-8")


def test_save_with_stale_revision_is_refused(client, engine, datasets_dir):
    (datasets_dir / "a.csv").write_text("id\n1\n", encoding="utf-8")
    dataset_id = _add_dataset(engine, "a.csv")
    body = client.get(f"/datasets/{dataset_id}/rows").json()

    (datasets_dir / "a.csv").write_text("id\n1\n2\n", encoding="utf-8")

    response = client.put(
        f"/datasets/{dataset_id}/rows",
        json={"rows": [{"id": "9"}], "revision": body["revision"]},
    )
    assert response.status_code == 409
    assert (datasets_dir / "a.csv").read_text(encoding="utf-8") == "id\n1\n2\n"


def test_json_list_keeps_value_types(client, engine, datasets_dir):
    rows = [{"q": "a", "score": 3}, {"q": "b", "score": 4.5}]
    (datasets_dir / "a.json").write_text(json.dumps(rows), encoding="utf-8")
    dataset_id = _add_dataset(engine, "a.json")

    body = client.get(f"/datasets/{dataset_id}/rows").json()
    assert body["headers"] == ["q", "score"]
    assert body["rows"] == rows

    rows[0]["score"] = 5
    client.put(
        f"/datasets/{dataset_id}/rows",
        json={"rows": rows, "revision": body["revision"]},
    )
    assert json.loads((datasets_dir / "a.json").read_text(encoding="utf-8")) == rows


def test_single_object_json_is_read_only(client, engine, datasets_dir):
    (datasets_dir / "a.json").write_text('{"a": 1}', encoding="utf-8")
    dataset_id = _add_dataset(engine, "a.json")

    body = client.get(f"/datasets/{dataset_id}/rows").json()
    assert body["read_only_reason"]

    response = client.put(
        f"/datasets/{dataset_id}/rows",
        json={"rows": [], "revision": body["revision"]},
    )
    assert response.status_code == 400


def test_csv_with_duplicate_columns_is_read_only(client, engine, datasets_dir):
    (datasets_dir / "a.csv").write_text("a,a\n1,2\n", encoding="utf-8")
    dataset_id = _add_dataset(engine, "a.csv")

    assert client.get(f"/datasets/{dataset_id}/rows").json()["read_only_reason"]


def test_dataset_over_the_row_limit_is_refused(
    client, engine, datasets_dir, monkeypatch
):
    monkeypatch.setattr(dataset_rows, "MAX_ROWS", 2)
    (datasets_dir / "a.csv").write_text("id\n1\n2\n3\n", encoding="utf-8")
    dataset_id = _add_dataset(engine, "a.csv")

    assert client.get(f"/datasets/{dataset_id}/rows").status_code == 413
