"""
The workspaces boundary, through the real application: who may reach a
workspace, what each role may do there, and that nothing leaks across.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

import config
from api import events as events_api
from auth.workspaces import (
    MembershipError,
    WorkspaceContext,
    claim_default_workspace,
    remove_member,
    set_member,
)
from schemas.events import RunEvent, RunState
from tables import Membership, Tag, User, Workspace
from tests.auth.people import add_member

# ---------------------------------------------------------------------------
# Creating and listing workspaces
# ---------------------------------------------------------------------------


def test_a_new_workspace_is_owned_by_its_creator(alice):
    slug = alice.create_workspace("Team Alpha")

    assert slug == "team-alpha"
    assert alice.get("/workspaces").json() == [
        {"slug": "team-alpha", "name": "Team Alpha", "role": "owner", "archived": False}
    ]


def test_slugs_are_unique_and_ascii(alice, bob):
    assert alice.create_workspace("Équipe  Été!") == "equipe-ete"
    assert bob.create_workspace("Équipe  Été!") == "equipe-ete-2"


def test_you_only_list_your_own_workspaces(alice, bob):
    alice.create_workspace("Alice's")
    bob.create_workspace("Bob's")

    assert [w["slug"] for w in alice.get("/workspaces").json()] == ["alice-s"]


def test_workspace_creation_can_be_reserved_to_admins(alice, bob, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACE_CREATION", "admins")
    monkeypatch.setattr(config, "INSTANCE_ADMINS", [alice.email])

    assert bob.post("/workspaces", json={"name": "Nope"}).status_code == 403
    assert alice.post("/workspaces", json={"name": "Ok"}).status_code == 201
    assert bob.get("/auth/me").json()["can_create_workspace"] is False
    assert alice.get("/auth/me").json()["can_create_workspace"] is True


def test_a_workspace_needs_a_name(alice):
    assert alice.post("/workspaces", json={"name": "   "}).status_code == 422


# ---------------------------------------------------------------------------
# Getting in
# ---------------------------------------------------------------------------

SCOPED_READS = [
    "datasets", "models", "prompts", "prompt-versions", "agents", "agent-teams",
    "tags", "batches", "analyses", "analyses/executions", "executions",
    "experiments", "dashboard", "providers", "events",
]  # fmt: skip


@pytest.mark.parametrize("path", SCOPED_READS)
def test_an_outsider_cannot_tell_a_workspace_exists(alice, bob, path):
    slug = alice.create_workspace("Private")

    assert bob.get(f"/workspaces/{slug}/{path}").status_code == 404
    assert bob.get(f"/workspaces/nowhere/{path}").status_code == 404


@pytest.mark.parametrize("path", [p for p in SCOPED_READS if p != "events"])
def test_a_member_reads_every_listing(alice, path):
    slug = alice.create_workspace("Mine")

    assert alice.get(f"/workspaces/{slug}/{path}").status_code == 200


def test_the_workspace_routes_need_a_session(app):
    client = TestClient(app)

    assert client.get("/workspaces").status_code == 401
    assert client.get("/workspaces/x/datasets").status_code == 401


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

WRITES = [
    ("post", "tags", {"name": "t"}),
    ("post", "models", {"name": "m", "provider": "mistral"}),
    ("post", "prompts", {"name": "p"}),
    ("post", "agent-teams", {"name": "t"}),
    ("post", "datasets", {"name": "d"}),
]


@pytest.mark.parametrize(("method", "path", "body"), WRITES)
def test_a_viewer_reads_but_cannot_write(engine, alice, bob, method, path, body):
    slug = alice.create_workspace("Shared")
    add_member(engine, slug, bob, "viewer")

    assert bob.get(f"/workspaces/{slug}/{path}").status_code == 200
    response = getattr(bob, method)(f"/workspaces/{slug}/{path}", json=body)
    assert response.status_code == 403
    assert "editor" in response.json()["detail"]


@pytest.mark.parametrize(("method", "path", "body"), WRITES)
def test_an_editor_can_write(engine, alice, bob, method, path, body):
    slug = alice.create_workspace("Shared")
    add_member(engine, slug, bob, "editor")

    response = getattr(bob, method)(f"/workspaces/{slug}/{path}", json=body)

    assert response.status_code == 201, response.text


def test_a_viewer_cannot_change_or_delete(engine, alice, bob):
    slug = alice.create_workspace("Shared")
    tag = alice.post(f"/workspaces/{slug}/tags", json={"name": "t"}).json()
    add_member(engine, slug, bob, "viewer")

    assert (
        bob.put(f"/workspaces/{slug}/tags/{tag['id']}", json={"name": "u"}).status_code
        == 403
    )
    assert bob.delete(f"/workspaces/{slug}/tags/{tag['id']}").status_code == 403
    assert alice.get(f"/workspaces/{slug}/tags").json()[0]["name"] == "t"


def test_a_viewer_may_run_read_only_computations(engine, alice, bob):
    slug = alice.create_workspace("Shared")
    add_member(engine, slug, bob, "viewer")

    body = {"formulas": []}
    response = bob.post(f"/workspaces/{slug}/aggregators/check", json=body)

    assert response.status_code == 200, response.text


def test_only_an_owner_can_rename_a_workspace(engine, alice, bob):
    slug = alice.create_workspace("Shared")
    add_member(engine, slug, bob, "editor")

    assert (
        bob.patch(f"/workspaces/{slug}", json={"name": "Mine now"}).status_code == 403
    )
    response = alice.patch(f"/workspaces/{slug}", json={"name": "Renamed"})
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"
    assert response.json()["slug"] == slug


def test_an_archived_workspace_is_read_only(engine, alice):
    slug = alice.create_workspace("Old")
    with Session(engine) as db:
        workspace = db.exec(select(Workspace).where(Workspace.slug == slug)).one()
        workspace.archived_at = workspace.created_at
        db.add(workspace)
        db.commit()

    assert alice.get(f"/workspaces/{slug}/tags").status_code == 200
    response = alice.post(f"/workspaces/{slug}/tags", json={"name": "t"})
    assert response.status_code == 409
    assert alice.get("/workspaces").json()[0]["archived"] is True


def test_writes_still_need_the_csrf_token(alice):
    slug = alice.create_workspace("Mine")

    response = alice.client.post(f"/workspaces/{slug}/tags", json={"name": "t"})

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Isolation between workspaces
# ---------------------------------------------------------------------------

RESOURCES = [
    ("datasets", {"name": "d"}),
    ("models", {"name": "m", "provider": "mistral"}),
    ("prompts", {"name": "p"}),
    ("agent-teams", {"name": "t"}),
    ("tags", {"name": "t"}),
    (
        "analyses",
        {
            "name": "a",
            "config": {
                "truth_column": "s",
                "value_type": "numeric",
                "metrics": ["rmse"],
            },
            "runs": [],
        },
    ),
]


@pytest.fixture
def two_workspaces(alice):
    return alice.create_workspace("First"), alice.create_workspace("Second")


@pytest.mark.parametrize(("path", "body"), RESOURCES)
def test_another_workspaces_ids_are_not_found(alice, two_workspaces, path, body):
    first, second = two_workspaces
    created = alice.post(f"/workspaces/{first}/{path}", json=body)
    assert created.status_code == 201, created.text
    item = f"/workspaces/{second}/{path}/{created.json()['id']}"

    assert alice.get(f"/workspaces/{second}/{path}").json() == []
    if path != "tags":  # tags have no GET by id
        assert alice.get(item).status_code == 404
    assert alice.put(item, json=body).status_code in (404, 405)
    assert alice.delete(item).status_code == 404
    # ...and the first workspace still has it
    assert len(alice.get(f"/workspaces/{first}/{path}").json()) == 1


def test_responses_do_not_expose_the_workspace_or_the_author(alice, two_workspaces):
    first, _ = two_workspaces
    for path, body in RESOURCES:
        created = alice.post(f"/workspaces/{first}/{path}", json=body).json()
        assert "workspace_id" not in created
        assert "created_by" not in created


def test_the_author_is_recorded(engine, alice, two_workspaces):
    first, _ = two_workspaces
    alice.post(f"/workspaces/{first}/tags", json={"name": "t"})

    with Session(engine) as db:
        assert db.exec(select(Tag.created_by)).one() == alice.id


def test_tag_names_are_unique_within_a_workspace_only(alice, two_workspaces):
    first, second = two_workspaces

    assert (
        alice.post(f"/workspaces/{first}/tags", json={"name": "Eval"}).status_code
        == 201
    )
    assert (
        alice.post(f"/workspaces/{second}/tags", json={"name": "eval"}).status_code
        == 201
    )
    assert (
        alice.post(f"/workspaces/{first}/tags", json={"name": "EVAL"}).status_code
        == 409
    )


def test_an_agent_cannot_point_at_another_workspaces_team(alice, two_workspaces):
    first, second = two_workspaces
    team = alice.post(f"/workspaces/{first}/agent-teams", json={"name": "t"}).json()

    response = alice.post(
        f"/workspaces/{second}/agents", json={"name": "a", "team_id": team["id"]}
    )

    assert response.status_code == 422
    assert "not found" in response.json()["detail"]


def test_an_agent_cannot_default_to_another_workspaces_model(alice, two_workspaces):
    first, second = two_workspaces
    model = alice.post(
        f"/workspaces/{first}/models", json={"name": "m", "provider": "mistral"}
    ).json()
    own_team = alice.post(
        f"/workspaces/{second}/agent-teams", json={"name": "t"}
    ).json()

    created = alice.post(
        f"/workspaces/{second}/agents",
        json={"name": "a", "team_id": own_team["id"], "default_model_id": model["id"]},
    )
    assert created.status_code == 422

    agent = alice.post(
        f"/workspaces/{second}/agents", json={"name": "a", "team_id": own_team["id"]}
    ).json()
    updated = alice.put(
        f"/workspaces/{second}/agents/{agent['id']}",
        json={"default_model_id": model["id"]},
    )
    assert updated.status_code == 422


def test_an_experiment_cannot_use_another_workspaces_dataset(alice, two_workspaces):
    first, second = two_workspaces
    dataset = alice.post(f"/workspaces/{first}/datasets", json={"name": "d"}).json()

    response = alice.post(
        f"/workspaces/{second}/experiments",
        json={"name": "e", "dataset_id": dataset["id"]},
    )

    assert response.status_code == 422
    assert "Dataset" in response.json()["detail"]


def test_an_experiment_cannot_use_another_workspaces_agents(alice, two_workspaces):
    first, second = two_workspaces
    own_dataset = alice.post(
        f"/workspaces/{second}/datasets", json={"name": "d"}
    ).json()
    team = alice.post(f"/workspaces/{first}/agent-teams", json={"name": "t"}).json()
    agent = alice.post(
        f"/workspaces/{first}/agents", json={"name": "a", "team_id": team["id"]}
    ).json()

    response = alice.post(
        f"/workspaces/{second}/experiments",
        json={
            "name": "e",
            "dataset_id": own_dataset["id"],
            "agent_teams": [str(team["id"])],
            "agent_configurations": {str(agent["id"]): {"is_active": True}},
        },
    )

    assert response.status_code == 422


def test_tags_cannot_be_put_on_another_workspaces_items(alice, two_workspaces):
    first, second = two_workspaces
    foreign_prompt = alice.post(
        f"/workspaces/{first}/prompts", json={"name": "p"}
    ).json()
    own_tag = alice.post(f"/workspaces/{second}/tags", json={"name": "t"}).json()
    foreign_tag = alice.post(f"/workspaces/{first}/tags", json={"name": "t"}).json()
    own_prompt = alice.post(f"/workspaces/{second}/prompts", json={"name": "p"}).json()

    on_foreign_item = alice.post(
        f"/workspaces/{second}/tags/assign",
        json={
            "kind": "prompt",
            "item_ids": [foreign_prompt["id"]],
            "add": [own_tag["id"]],
            "remove": [],
        },
    )
    with_foreign_tag = alice.post(
        f"/workspaces/{second}/tags/assign",
        json={
            "kind": "prompt",
            "item_ids": [own_prompt["id"]],
            "add": [foreign_tag["id"]],
            "remove": [],
        },
    )
    at_creation = alice.post(
        f"/workspaces/{second}/prompts",
        json={"name": "q", "tag_ids": [foreign_tag["id"]]},
    )

    assert on_foreign_item.status_code == 422
    assert with_foreign_tag.status_code == 422
    assert at_creation.status_code == 422


def test_an_analysis_cannot_compare_another_workspaces_executions(
    engine, alice, two_workspaces
):
    _, second = two_workspaces
    config = {"truth_column": "s", "value_type": "numeric", "metrics": ["rmse"]}

    response = alice.post(
        f"/workspaces/{second}/analyses",
        json={
            "name": "a",
            "config": config,
            "runs": [{"execution_id": 1, "agent_name": "g"}],
        },
    )

    assert response.status_code == 422


def test_the_dashboard_only_counts_its_workspace(engine, alice, two_workspaces):
    first, second = two_workspaces
    alice.post(f"/workspaces/{first}/datasets", json={"name": "d"})

    body = alice.get(f"/workspaces/{second}/dashboard").json()

    assert body["recent_experiments"] == []
    assert body["activity"]["current"]["experiments"] == 0


# ---------------------------------------------------------------------------
# Live runs
# ---------------------------------------------------------------------------


def test_the_live_stream_only_tells_a_workspace_about_its_own_runs(engine, monkeypatch):
    import event_bus

    monkeypatch.setattr(events_api, "engine", engine)
    context = WorkspaceContext(
        id=1, slug="test", name="Test", role="viewer", archived=False, user_id=1
    )

    def run(experiment_id: int, workspace_id: int) -> RunEvent:
        state = RunState(experiment_id=experiment_id, status="running")
        return RunEvent(name="progress", state=state, workspace_id=workspace_id)

    async def first_event():
        stream = events_api.stream_events(context)
        pending = asyncio.ensure_future(anext(stream))
        await asyncio.sleep(0)  # let it subscribe
        event_bus.publish(run(experiment_id=99, workspace_id=2))
        event_bus.publish(run(experiment_id=7, workspace_id=1))
        event = await asyncio.wait_for(pending, 2)
        await stream.aclose()
        return event

    event = asyncio.run(first_event())

    assert event.data.experiment_id == 7


# ---------------------------------------------------------------------------
# Membership rules
# ---------------------------------------------------------------------------


def test_the_last_owner_cannot_leave_or_step_down(engine, alice):
    slug = alice.create_workspace("Mine")
    with Session(engine) as db:
        workspace = db.exec(select(Workspace).where(Workspace.slug == slug)).one()
        user = db.get(User, alice.id)

        with pytest.raises(MembershipError, match="at least one owner"):
            remove_member(db, workspace, user)
        with pytest.raises(MembershipError, match="at least one owner"):
            set_member(db, workspace, user, "editor")


def test_an_owner_can_step_down_once_another_owns(engine, alice, bob):
    slug = alice.create_workspace("Mine")
    add_member(engine, slug, bob, "owner")

    with Session(engine) as db:
        workspace = db.exec(select(Workspace).where(Workspace.slug == slug)).one()
        set_member(db, workspace, db.get(User, alice.id), "viewer")

    assert alice.get("/workspaces").json()[0]["role"] == "viewer"


def test_an_unknown_role_is_refused(engine, alice, bob):
    slug = alice.create_workspace("Mine")
    with Session(engine) as db:
        workspace = db.exec(select(Workspace).where(Workspace.slug == slug)).one()
        with pytest.raises(MembershipError, match="Unknown role"):
            set_member(db, workspace, db.get(User, bob.id), "admin")


# ---------------------------------------------------------------------------
# The workspace the existing data moved to
# ---------------------------------------------------------------------------


@pytest.fixture
def default_workspace(engine):
    with Session(engine) as db:
        workspace = Workspace(slug="default", name="Default")
        db.add(workspace)
        db.commit()
        return workspace.id


def test_the_first_instance_admin_to_sign_in_owns_the_default_workspace(
    engine, alice, bob, default_workspace, monkeypatch
):
    monkeypatch.setattr(config, "INSTANCE_ADMINS", [alice.email, bob.email])

    with Session(engine) as db:
        claim_default_workspace(db, db.get(User, alice.id))
        claim_default_workspace(db, db.get(User, bob.id))
        members = db.exec(
            select(Membership).where(Membership.workspace_id == default_workspace)
        ).all()

    assert [(m.user_id, m.role) for m in members] == [(alice.id, "owner")]


def test_an_ordinary_user_does_not_claim_the_default_workspace(
    engine, bob, default_workspace
):
    with Session(engine) as db:
        claim_default_workspace(db, db.get(User, bob.id))
        assert db.exec(select(Membership)).all() == []


def test_without_members_the_default_workspace_is_unreachable(bob, default_workspace):
    assert bob.get("/workspaces/default/datasets").status_code == 404
