"""What each role may do with studies and notes, and what stays inside a workspace."""

import pytest
from sqlmodel import Session, select

from tables import Dataset, Experiment, Workspace
from tests.auth.people import Person, add_member
from workspace_scope import scope_session


@pytest.fixture
def carol(engine, app):
    return Person(engine, "carol")


@pytest.fixture
def team(alice, bob, carol, engine):
    """alice owns it, bob edits, carol only reads."""
    slug = alice.create_workspace("Team")
    add_member(engine, slug, bob, "editor")
    add_member(engine, slug, carol, "viewer")
    return slug


def add_experiment(engine, slug: str) -> int:
    with Session(engine) as db:
        workspace = db.exec(select(Workspace).where(Workspace.slug == slug)).one()
        scope_session(db, workspace.id)
        dataset = Dataset(name="answers", file_path="answers.csv")
        db.add(dataset)
        db.flush()
        experiment = Experiment(name="Run", dataset_id=dataset.id)
        db.add(experiment)
        db.commit()
        return experiment.id


def test_editors_write_viewers_only_read(alice, bob, carol, team, engine):
    experiment = add_experiment(engine, team)
    base = f"/workspaces/{team}"

    created = bob.post(f"{base}/studies", json={"name": "Prompt v3"})
    assert created.status_code == 201
    study = created.json()
    assert study["author"]["display_name"] == "Bob"

    assert carol.post(f"{base}/studies", json={"name": "No"}).status_code == 403
    items = {"items": [{"kind": "experiment", "item_id": experiment}]}
    assert (
        carol.post(f"{base}/studies/{study['id']}/items", json=items).status_code == 403
    )
    assert (
        bob.post(f"{base}/studies/{study['id']}/items", json=items).status_code == 200
    )

    note = {"kind": "study", "item_id": study["id"], "body": "Hello"}
    assert carol.post(f"{base}/notes", json=note).status_code == 403
    written = bob.post(f"{base}/notes", json=note).json()

    seen = carol.get(
        f"{base}/notes", params={"kind": "study", "item_id": study["id"]}
    ).json()
    assert [(n["body"], n["can_edit"], n["can_delete"]) for n in seen] == [
        ("Hello", False, False)
    ]
    assert carol.get(f"{base}/studies/{study['id']}").status_code == 200
    assert carol.get(f"{base}/studies/{study['id']}/activity").status_code == 200

    # The author edits; the owner may delete it but not rewrite it
    assert (
        alice.put(f"{base}/notes/{written['id']}", json={"body": "x"}).status_code
        == 403
    )
    owner_view = alice.get(
        f"{base}/notes", params={"kind": "study", "item_id": study["id"]}
    ).json()
    assert [(n["can_edit"], n["can_delete"]) for n in owner_view] == [(False, True)]
    assert alice.delete(f"{base}/notes/{written['id']}").status_code == 204


def test_a_workspace_never_sees_the_studies_of_another(alice, bob, team, engine):
    other = bob.create_workspace("Other")
    experiment = add_experiment(engine, team)
    study = alice.post(
        f"/workspaces/{team}/studies",
        json={
            "name": "Private",
            "items": [{"kind": "experiment", "item_id": experiment}],
        },
    ).json()

    # Bob belongs to both: an item of one workspace is unknown to the other
    assert bob.get(f"/workspaces/{other}/studies").json() == []
    assert bob.get(f"/workspaces/{other}/studies/{study['id']}").status_code == 404
    refused = bob.post(
        f"/workspaces/{other}/studies",
        json={"name": "Mine", "items": [{"kind": "experiment", "item_id": experiment}]},
    )
    assert refused.status_code == 422


def test_an_archived_workspace_is_read_only_for_studies(alice, team, engine):
    base = f"/workspaces/{team}"
    study = alice.post(f"{base}/studies", json={"name": "Old"}).json()
    assert alice.post(f"{base}/archive").status_code in (200, 204)

    assert alice.get(f"{base}/studies/{study['id']}").status_code == 200
    assert alice.post(f"{base}/studies", json={"name": "New"}).status_code == 409
    note = {"kind": "study", "item_id": study["id"], "body": "late"}
    assert alice.post(f"{base}/notes", json=note).status_code == 409
