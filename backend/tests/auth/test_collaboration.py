"""Members, invitation links, and archiving or deleting a workspace."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlmodel import Session, SQLModel, select

import config
import workspace_files
import workspace_lifecycle
from tables import (
    Agent,
    AgentExecutionSnapshot,
    AgentTeam,
    Analysis,
    Batch,
    Dataset,
    Experiment,
    ExperimentAgentConfig,
    ExperimentExecution,
    Invitation,
    Membership,
    Model,
    Prompt,
    PromptVersion,
    Tag,
    TagLink,
    User,
    Workspace,
    WorkspaceCredential,
    WorkspaceOwned,
)
from tests.auth.people import Person, add_member


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


def roles(person, slug):
    return {m["display_name"]: m["role"] for m in person.get(f"/workspaces/{slug}/members").json()}


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


def test_every_member_sees_who_is_in_the_workspace_owners_first(alice, bob, carol, team):
    members = carol.get(f"/workspaces/{team}/members").json()

    assert [(m["display_name"], m["role"]) for m in members] == [
        ("Alice", "owner"),
        ("Bob", "editor"),
        ("Carol", "viewer"),
    ]
    assert members[0]["email"] == "alice@irit.fr"


def test_strangers_do_not_see_the_members(alice, team, engine, app):
    stranger = Person(engine, "dave")

    assert stranger.get(f"/workspaces/{team}/members").status_code == 404


def test_an_owner_adds_someone_who_signed_in_before(alice, team, engine, app):
    Person(engine, "dave")

    response = alice.post(
        f"/workspaces/{team}/members", json={"email": "Dave@IRIT.fr", "role": "editor"}
    )

    assert response.status_code == 201
    assert response.json()["role"] == "editor"
    assert roles(alice, team)["Dave"] == "editor"


def test_adding_someone_unknown_points_to_invitations(alice, team):
    response = alice.post(
        f"/workspaces/{team}/members", json={"email": "ghost@irit.fr", "role": "viewer"}
    )

    assert response.status_code == 404
    assert "invitation" in response.json()["detail"]


def test_adding_a_member_twice_is_refused(alice, bob, team):
    response = alice.post(
        f"/workspaces/{team}/members", json={"email": bob.email, "role": "viewer"}
    )

    assert response.status_code == 409
    assert roles(alice, team)["Bob"] == "editor"


def test_someone_deactivated_cannot_be_added(alice, team, engine, app):
    dave = Person(engine, "dave")
    with Session(engine) as db:
        user = db.get(User, dave.id)
        user.is_active = False
        db.add(user)
        db.commit()

    response = alice.post(
        f"/workspaces/{team}/members", json={"email": dave.email, "role": "viewer"}
    )

    assert response.status_code == 404


def test_several_accounts_with_one_email_are_never_guessed_between(alice, team, engine, app):
    first = Person(engine, "dave")
    with Session(engine) as db:
        db.add(User(display_name="Dave 2", email=first.email))
        db.commit()

    response = alice.post(
        f"/workspaces/{team}/members", json={"email": first.email, "role": "viewer"}
    )

    assert response.status_code == 409


def test_only_owners_manage_members(alice, bob, carol, team, engine, app):
    dave = Person(engine, "dave")

    for person in (bob, carol):
        assert (
            person.post(
                f"/workspaces/{team}/members", json={"email": dave.email, "role": "viewer"}
            ).status_code
            == 403
        )
        assert (
            person.put(f"/workspaces/{team}/members/{carol.id}", json={"role": "owner"}).status_code
            == 403
        )
        assert person.delete(f"/workspaces/{team}/members/{alice.id}").status_code == 403


def test_an_unknown_role_is_refused(alice, bob, team):
    response = alice.put(f"/workspaces/{team}/members/{bob.id}", json={"role": "admin"})

    assert response.status_code == 422


def test_an_owner_changes_a_role(alice, bob, team):
    response = alice.put(f"/workspaces/{team}/members/{bob.id}", json={"role": "owner"})

    assert response.status_code == 200
    assert roles(alice, team)["Bob"] == "owner"


def test_the_last_owner_cannot_be_demoted_or_removed(alice, team):
    demoted = alice.put(f"/workspaces/{team}/members/{alice.id}", json={"role": "editor"})
    removed = alice.delete(f"/workspaces/{team}/members/{alice.id}")

    assert demoted.status_code == 409
    assert removed.status_code == 409
    assert roles(alice, team)["Alice"] == "owner"


def deactivate(engine, person):
    with Session(engine) as db:
        user = db.get(User, person.id)
        user.is_active = False
        db.add(user)
        db.commit()


def test_an_owner_who_can_no_longer_sign_in_does_not_count_as_the_remaining_owner(
    alice, bob, team, engine
):
    alice.put(f"/workspaces/{team}/members/{bob.id}", json={"role": "owner"})
    deactivate(engine, bob)

    assert alice.delete(f"/workspaces/{team}/members/{alice.id}").status_code == 409
    assert alice.put(f"/workspaces/{team}/members/{alice.id}", json={"role": "editor"}).status_code == 409
    # ...while the inactive one can be removed, and nothing is left in doubt
    assert alice.delete(f"/workspaces/{team}/members/{bob.id}").status_code == 204


def test_two_owners_cannot_leave_at_the_same_time(alice, bob, team, engine):
    from sqlalchemy.exc import OperationalError

    from auth.workspaces import _lock, remove_member

    alice.put(f"/workspaces/{team}/members/{bob.id}", json={"role": "owner"})
    with Session(engine) as first, Session(engine) as second:
        workspace = first.exec(select(Workspace).where(Workspace.slug == team)).one()
        _lock(first, workspace)  # the first departure is under way

        second.exec(text("SET LOCAL lock_timeout = '300ms'"))
        with pytest.raises(OperationalError):
            remove_member(second, second.get(Workspace, workspace.id), second.get(User, bob.id))
        second.rollback()
        first.rollback()

    assert roles(alice, team)["Bob"] == "owner"


def test_an_owner_removes_a_member_who_then_loses_access(alice, bob, team):
    assert alice.delete(f"/workspaces/{team}/members/{bob.id}").status_code == 204

    assert bob.get(f"/workspaces/{team}/members").status_code == 404
    assert "Bob" not in roles(alice, team)


def test_anyone_may_leave_a_workspace(alice, carol, team):
    assert carol.delete(f"/workspaces/{team}/members/{carol.id}").status_code == 204

    assert carol.get(f"/workspaces/{team}/datasets").status_code == 404


def test_changing_the_role_of_someone_outside_is_a_404(alice, team, engine, app):
    dave = Person(engine, "dave")

    assert alice.put(f"/workspaces/{team}/members/{dave.id}", json={"role": "viewer"}).status_code == 404
    assert alice.delete(f"/workspaces/{team}/members/{dave.id}").status_code == 404


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


def invite(owner, slug, role="editor") -> str:
    response = owner.post(f"/workspaces/{slug}/invitations", json={"role": role})
    assert response.status_code == 201, response.text
    return response.json()["token"]


def test_an_invitation_adds_whoever_opens_it_with_the_role(alice, team, engine, app):
    dave = Person(engine, "dave")
    token = invite(alice, team, "editor")

    seen = dave.post("/invitations/preview", json={"token": token})
    joined = dave.post("/invitations/accept", json={"token": token})

    assert seen.json() == {"workspace_name": "Team", "role": "editor", "invited_by": "Alice"}
    assert joined.json() == {"slug": team, "name": "Team", "role": "editor", "joined": True}
    assert roles(alice, team)["Dave"] == "editor"


def test_an_invitation_works_once(alice, team, engine, app):
    dave, erin = Person(engine, "dave"), Person(engine, "erin")
    token = invite(alice, team)

    assert dave.post("/invitations/accept", json={"token": token}).status_code == 200

    assert erin.post("/invitations/accept", json={"token": token}).status_code == 404
    assert erin.post("/invitations/preview", json={"token": token}).status_code == 404
    assert "Erin" not in roles(alice, team)


def test_only_a_hash_of_the_token_is_kept(alice, team, engine):
    token = invite(alice, team)

    with Session(engine) as db:
        stored = db.exec(select(Invitation)).one()
    assert token not in stored.token_hash
    assert token not in str(stored.model_dump())


def test_the_list_never_shows_tokens_and_hides_used_ones(alice, team, engine, app):
    dave = Person(engine, "dave")
    used, open_ = invite(alice, team), invite(alice, team, "viewer")
    dave.post("/invitations/accept", json={"token": used})

    listed = alice.get(f"/workspaces/{team}/invitations")

    assert [i["role"] for i in listed.json()] == ["viewer"]
    assert open_ not in listed.text


def test_a_revoked_invitation_stops_working(alice, team, engine, app):
    dave = Person(engine, "dave")
    token = invite(alice, team)
    (item,) = alice.get(f"/workspaces/{team}/invitations").json()

    assert alice.delete(f"/workspaces/{team}/invitations/{item['id']}").status_code == 204

    assert dave.post("/invitations/accept", json={"token": token}).status_code == 404
    assert alice.delete(f"/workspaces/{team}/invitations/{item['id']}").status_code == 404


def test_an_invitation_expires(alice, team, engine, app):
    dave = Person(engine, "dave")
    token = invite(alice, team)
    with Session(engine) as db:
        stored = db.exec(select(Invitation)).one()
        stored.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.add(stored)
        db.commit()

    assert dave.post("/invitations/accept", json={"token": token}).status_code == 404
    assert alice.get(f"/workspaces/{team}/invitations").json() == []


def test_the_lifetime_of_a_link_is_configurable(alice, team, monkeypatch):
    monkeypatch.setattr(config, "INVITATION_DAYS", 1)

    response = alice.post(f"/workspaces/{team}/invitations", json={"role": "viewer"}).json()

    created = datetime.fromisoformat(response["created_at"])
    expires = datetime.fromisoformat(response["expires_at"])
    assert abs(expires - created - timedelta(days=1)) < timedelta(seconds=5)


def test_a_member_who_opens_a_link_keeps_their_role_and_the_link_stays_valid(alice, bob, team, engine, app):
    dave = Person(engine, "dave")
    token = invite(alice, team, "viewer")

    again = bob.post("/invitations/accept", json={"token": token})

    assert again.json()["joined"] is False
    assert again.json()["role"] == "editor"
    assert dave.post("/invitations/accept", json={"token": token}).status_code == 200


def test_an_invitation_never_makes_an_owner(alice, team):
    response = alice.post(f"/workspaces/{team}/invitations", json={"role": "owner"})

    assert response.status_code == 422


def test_only_owners_make_invitations(bob, carol, team):
    for person in (bob, carol):
        assert person.post(f"/workspaces/{team}/invitations", json={"role": "viewer"}).status_code == 403
        assert person.get(f"/workspaces/{team}/invitations").status_code == 403


def test_an_unknown_link_is_a_404_and_a_signed_out_visitor_is_a_401(alice, team, app):
    token = invite(alice, team)
    from fastapi.testclient import TestClient

    import main

    assert alice.post("/invitations/preview", json={"token": "not-a-token"}).status_code == 404
    assert TestClient(main.app).post("/invitations/preview", json={"token": token}).status_code == 401


# ---------------------------------------------------------------------------
# Archiving and deleting
# ---------------------------------------------------------------------------


def test_an_archived_workspace_is_read_only_for_everyone(alice, bob, team):
    assert alice.post(f"/workspaces/{team}/archive").json()["archived"] is True

    assert bob.post(f"/workspaces/{team}/tags", json={"name": "x", "color": "gray"}).status_code == 409
    assert bob.get(f"/workspaces/{team}/tags").status_code == 200
    assert alice.get("/workspaces").json()[0]["archived"] is True


def test_only_owners_archive(bob, carol, team):
    assert bob.post(f"/workspaces/{team}/archive").status_code == 403
    assert carol.post(f"/workspaces/{team}/unarchive").status_code == 403


def test_archiving_forgets_the_api_keys_and_the_invitations(alice, team, engine, app, monkeypatch):
    monkeypatch.setattr(config, "ENCRYPTION_KEY", "e" * 40)
    alice.put(f"/workspaces/{team}/providers/mistral/key", json={"api_key": "sk-0123456789"})
    token = invite(alice, team)
    dave = Person(engine, "dave")

    alice.post(f"/workspaces/{team}/archive")

    with Session(engine) as db:
        assert db.exec(select(WorkspaceCredential)).all() == []
    assert dave.post("/invitations/accept", json={"token": token}).status_code == 404


def test_an_archived_workspace_can_be_reopened(alice, team):
    alice.post(f"/workspaces/{team}/archive")

    assert alice.post(f"/workspaces/{team}/unarchive").json()["archived"] is False
    assert alice.post(f"/workspaces/{team}/tags", json={"name": "x", "color": "gray"}).status_code == 201


def test_members_can_still_leave_an_archived_workspace(alice, carol, team):
    alice.post(f"/workspaces/{team}/archive")

    assert carol.delete(f"/workspaces/{team}/members/{carol.id}").status_code == 204


def test_archiving_stops_the_runs_of_the_workspace(alice, team, engine, monkeypatch):
    import async_jobs

    cancelled = []
    monkeypatch.setattr(async_jobs, "cancel_experiment", lambda eid: cancelled.append(eid))
    with Session(engine) as db:
        workspace_id = db.exec(select(Workspace).where(Workspace.slug == team)).one().id
        dataset = Dataset(name="d", workspace_id=workspace_id)
        db.add(dataset)
        db.flush()
        for status in ("running", "queued", "completed"):
            db.add(Experiment(name=status, dataset_id=dataset.id, status=status, workspace_id=workspace_id))
        db.commit()

    alice.post(f"/workspaces/{team}/archive")

    assert len(cancelled) == 2


def test_a_workspace_is_archived_before_it_is_deleted(alice, team):
    assert alice.delete(f"/workspaces/{team}?confirm={team}").status_code == 409

    alice.post(f"/workspaces/{team}/archive")

    assert alice.delete(f"/workspaces/{team}").status_code == 422
    assert alice.delete(f"/workspaces/{team}?confirm=wrong").status_code == 422
    assert alice.get(f"/workspaces/{team}").status_code == 200


def test_only_owners_delete(bob, alice, team):
    alice.post(f"/workspaces/{team}/archive")

    assert bob.delete(f"/workspaces/{team}?confirm={team}").status_code == 403


def populate(engine, workspace_id: int) -> None:
    """One row in every table a workspace owns, loops between tables included."""
    with Session(engine) as db:
        def add(row):
            row.workspace_id = workspace_id
            db.add(row)
            db.flush()
            return row

        dataset = add(Dataset(name="d", file_path="d.csv"))
        model = add(Model(name="m", provider="mistral"))
        prompt = add(Prompt(name="p"))
        version = add(PromptVersion(prompt_id=prompt.id, version="1"))
        team = add(AgentTeam(name="t"))
        agent = add(Agent(name="a", team_id=team.id, default_prompt_version_id=version.id, default_model_id=model.id))
        experiment = add(Experiment(name="e", dataset_id=dataset.id))
        batch = add(Batch(name="b", base_experiment_id=experiment.id))
        experiment.batch_id = batch.id
        add(
            ExperimentAgentConfig(
                experiment_id=experiment.id, agent_id=agent.id, model_id=model.id,
                prompt_version_id=version.id,
            )
        )
        execution = add(ExperimentExecution(experiment_id=experiment.id, dataset_snapshot="{}", results_file_path="r.json"))
        add(
            AgentExecutionSnapshot(
                execution_id=execution.id, agent_id=agent.id, agent_name_snapshot="a",
                model_name_snapshot="m", model_provider_snapshot="mistral",
                prompt_name_snapshot="p", prompt_version_snapshot="1", execution_order=1,
            )
        )
        add(Analysis(name="x", config="{}", runs="[]"))
        tag = add(Tag(name="t"))
        add(TagLink(tag_id=tag.id, kind="prompt", item_id=prompt.id))
        add(WorkspaceCredential(provider="mistral", ciphertext="x", last4="1234"))
        db.commit()


def test_deleting_a_workspace_removes_everything_in_it(alice, bob, team, engine, data_dir):
    with Session(engine) as db:
        mine = db.exec(select(Workspace).where(Workspace.slug == team)).one().id
    other_slug = alice.create_workspace("Other")
    with Session(engine) as db:
        theirs = db.exec(select(Workspace).where(Workspace.slug == other_slug)).one().id
    populate(engine, mine)
    populate(engine, theirs)
    for workspace_id in (mine, theirs):
        folder = workspace_files.datasets_dir(workspace_id)
        folder.mkdir(parents=True)
        (folder / "d.csv").write_text("a\n1\n")
    alice.post(f"/workspaces/{team}/archive")

    assert alice.delete(f"/workspaces/{team}?confirm={team}").status_code == 204

    with Session(engine) as db:
        assert db.get(Workspace, mine) is None
        assert db.exec(select(Membership).where(Membership.workspace_id == mine)).all() == []
        for table in workspace_lifecycle.DELETE_ORDER:
            assert db.exec(select(table).where(table.workspace_id == mine)).all() == [], table
            assert len(db.exec(select(table).where(table.workspace_id == theirs)).all()) >= 1, table
        assert db.get(Workspace, theirs) is not None
    assert not workspace_files.workspace_dir(mine).exists()
    assert (workspace_files.datasets_dir(theirs) / "d.csv").exists()
    assert bob.get(f"/workspaces/{team}").status_code == 404
    assert [w["slug"] for w in alice.get("/workspaces").json()] == [other_slug]


def test_the_delete_list_covers_every_table_a_workspace_owns():
    owned = {
        mapper.class_
        for mapper in SQLModel._sa_registry.mappers
        if issubclass(mapper.class_, WorkspaceOwned)
    }

    assert set(workspace_lifecycle.DELETE_ORDER) == owned
    assert len(workspace_lifecycle.DELETE_ORDER) == len(owned)


def test_the_delete_order_never_removes_a_row_before_the_rows_pointing_at_it():
    order = list(workspace_lifecycle.DELETE_ORDER)
    # These two make a loop; the deletion cuts them first
    cut = {("batch", "experiment"), ("experiment", "batch")}
    for index, table in enumerate(order):
        for column in table.__table__.columns:
            for fk in column.foreign_keys:
                target = fk.column.table.name
                if target == table.__table__.name or (table.__table__.name, target) in cut:
                    continue
                referenced = [t for t in order if t.__table__.name == target]
                if referenced:
                    assert order.index(referenced[0]) > index, (table.__table__.name, target)

