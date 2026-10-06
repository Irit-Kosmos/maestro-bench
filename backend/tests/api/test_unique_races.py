"""Two requests can pass the same availability check: the unique index decides, and
the loser gets an answer, not a server error."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from api import tags
from auth import workspaces
from db import get_session
from tables import User, Workspace
from tests.conftest import TEST_WORKSPACE_ID
from workspace_scope import scope_session


@pytest.fixture
def client(engine):
    app = FastAPI()
    app.include_router(tags.router)

    def _session():
        with Session(engine) as session:
            scope_session(session, TEST_WORKSPACE_ID)
            yield session

    app.dependency_overrides[get_session] = _session
    return TestClient(app)


@pytest.fixture
def unchecked(monkeypatch):
    """The availability check always says yes: as if the other request had not committed yet."""
    monkeypatch.setattr(tags, "_name_taken", lambda *args, **kwargs: False)


def test_creating_a_tag_that_lost_the_race_is_a_409(client, unchecked):
    assert client.post("/tags", json={"name": "Dup"}).status_code == 201

    response = client.post("/tags", json={"name": "dup"})

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
    assert len(client.get("/tags").json()) == 1


def test_renaming_a_tag_that_lost_the_race_is_a_409(client, unchecked):
    client.post("/tags", json={"name": "A"})
    other = client.post("/tags", json={"name": "B"}).json()

    response = client.put(f"/tags/{other['id']}", json={"name": "a"})

    assert response.status_code == 409
    assert client.get("/tags").json()[1]["name"] == "B"


def test_a_workspace_whose_slug_was_taken_meanwhile_gets_the_next_one(
    engine, monkeypatch
):
    with Session(engine) as db:
        owner = User(display_name="Owner")
        db.add(owner)
        db.add(Workspace(slug="team", name="Team"))
        db.commit()
        db.refresh(owner)

        # The first look finds "team" free, as it was before the other request committed
        slugs = iter(["team", "team-2"])
        monkeypatch.setattr(workspaces, "free_slug", lambda *args: next(slugs))

        created = workspaces.create_workspace(db, "Team", owner.id)

        assert created.slug == "team-2"
        assert [w.slug for w in db.exec(select(Workspace)).all()].count("team") == 1
