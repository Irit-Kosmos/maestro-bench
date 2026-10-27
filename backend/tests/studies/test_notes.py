# MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
# Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
# Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Notes: a journal on an item or a study, edited by its author."""

from sqlmodel import Session

from tables import User
from tests.studies.conftest import make_experiment, make_study, ref


def write(client, kind, item_id, body="A note"):
    response = client.post(
        "/notes", json={"kind": kind, "item_id": item_id, "body": body}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_a_note_remembers_its_author_and_who_may_change_it(client, engine, alice):
    experiment = make_experiment(engine)

    note = write(client, "experiment", experiment, "F1 drops with prompt v3")

    assert note["author"]["display_name"] == "Alice"
    assert note["can_edit"] and note["can_delete"]
    assert note["created_at"] == note["updated_at"]


def test_the_journal_lists_the_newest_note_first(client, engine, alice):
    experiment = make_experiment(engine)
    other = make_experiment(engine, "Other")
    write(client, "experiment", experiment, "first")
    write(client, "experiment", experiment, "second")
    write(client, "experiment", other, "elsewhere")

    notes = client.get(
        "/notes", params={"kind": "experiment", "item_id": experiment}
    ).json()

    assert [n["body"] for n in notes] == ["second", "first"]


def test_a_note_needs_an_item_and_a_text(client, engine):
    experiment = make_experiment(engine)

    assert (
        client.post(
            "/notes", json={"kind": "batch", "item_id": 999, "body": "x"}
        ).status_code
        == 404
    )
    assert (
        client.get("/notes", params={"kind": "study", "item_id": 999}).status_code
        == 404
    )
    blank = {"kind": "experiment", "item_id": experiment, "body": "   "}
    assert client.post("/notes", json=blank).status_code == 422
    assert client.post("/notes", json={**blank, "body": ""}).status_code == 422
    assert (
        client.post(
            "/notes", json={**blank, "kind": "dataset", "body": "x"}
        ).status_code
        == 422
    )


def test_only_the_author_edits_a_note(client, engine, caller, alice, bob):
    experiment = make_experiment(engine)
    note = write(client, "experiment", experiment, "mine")

    caller.user_id, caller.role = bob.id, "editor"
    assert (
        client.put(f"/notes/{note['id']}", json={"body": "yours now"}).status_code
        == 403
    )
    listed = client.get(
        "/notes", params={"kind": "experiment", "item_id": experiment}
    ).json()
    assert listed[0]["body"] == "mine"
    assert not listed[0]["can_edit"]

    caller.user_id = alice.id
    edited = client.put(f"/notes/{note['id']}", json={"body": "edited"}).json()
    assert edited["body"] == "edited"
    assert edited["updated_at"] > edited["created_at"]


def test_an_owner_deletes_any_note_but_an_editor_only_their_own(
    client, engine, caller, alice, bob
):
    experiment = make_experiment(engine)
    note = write(client, "experiment", experiment)

    caller.user_id, caller.role = bob.id, "editor"
    assert client.delete(f"/notes/{note['id']}").status_code == 403

    caller.role = "owner"
    assert client.delete(f"/notes/{note['id']}").status_code == 204
    assert (
        client.get(
            "/notes", params={"kind": "experiment", "item_id": experiment}
        ).json()
        == []
    )
    assert client.delete(f"/notes/{note['id']}").status_code == 404


def test_the_author_deletes_their_own_note_without_being_an_owner(
    client, engine, caller, alice
):
    experiment = make_experiment(engine)
    note = write(client, "experiment", experiment)
    caller.role = "editor"

    assert client.delete(f"/notes/{note['id']}").status_code == 204


def test_a_note_of_a_deleted_author_stays_without_one(client, engine, alice):
    experiment = make_experiment(engine)
    write(client, "experiment", experiment)
    with Session(engine) as db:
        db.delete(db.get(User, alice.id))
        db.commit()

    notes = client.get(
        "/notes", params={"kind": "experiment", "item_id": experiment}
    ).json()

    assert notes[0]["author"] is None


def test_the_notes_of_an_archived_study_are_read_only(client, engine, alice):
    experiment = make_experiment(engine)
    study = make_study(client, items=[ref("experiment", experiment)])
    sid = study["id"]
    note = write(client, "study", sid, "conclusion")
    item_note = write(client, "experiment", experiment, "on the run")
    client.put(f"/studies/{sid}", json={"status": "archived"})

    refused = client.post(
        "/notes", json={"kind": "study", "item_id": sid, "body": "late"}
    )
    assert refused.status_code == 409
    assert client.put(f"/notes/{note['id']}", json={"body": "x"}).status_code == 409
    assert client.delete(f"/notes/{note['id']}").status_code == 409
    # The note of an item is the item's, whatever happens to its studies
    assert (
        client.put(f"/notes/{item_note['id']}", json={"body": "still ok"}).status_code
        == 200
    )
    assert (
        client.get("/notes", params={"kind": "study", "item_id": sid}).status_code
        == 200
    )


def test_a_note_about_a_study_makes_it_the_most_recently_touched(client, engine, alice):
    old, new = make_study(client, "old"), make_study(client, "new")

    write(client, "study", old["id"], "news")

    assert [s["name"] for s in client.get("/studies").json()] == ["old", "new"]
    assert new["id"] != old["id"]
