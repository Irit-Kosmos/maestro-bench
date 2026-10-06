"""Studies gather experiments, batches and analyses without owning them."""

import pytest
from sqlmodel import select

from tables import Note, StudyItem, TagLink
from tests.conftest import scoped
from tests.studies.conftest import (
    make_analysis,
    make_batch,
    make_experiment,
    make_study,
    ref,
)

# ---------------------------------------------------------------------------
# Creating and editing
# ---------------------------------------------------------------------------


def test_a_study_starts_active_with_a_trimmed_name_and_its_creator(client, alice):
    study = make_study(client, "  Prompt v3  ", description="# Why")

    assert study["name"] == "Prompt v3"
    assert study["description"] == "# Why"
    assert study["status"] == "active"
    assert study["author"]["display_name"] == "Alice"
    assert study["counts"] == {"experiments": 0, "batches": 0, "analyses": 0}
    assert study["items"] == []


def test_a_study_needs_a_name(client):
    assert client.post("/studies", json={"name": "   "}).status_code == 422
    assert client.post("/studies", json={"name": ""}).status_code == 422


def test_a_study_can_start_from_a_selection_and_tags(client, engine):
    experiment = make_experiment(engine)
    batch = make_batch(engine)
    tag = client.post("/tags", json={"name": "wip"}).json()

    study = make_study(
        client,
        items=[ref("experiment", experiment), ref("batch", batch)],
        tag_ids=[tag["id"]],
    )

    assert study["counts"] == {"experiments": 1, "batches": 1, "analyses": 0}
    assert [t["name"] for t in study["tags"]] == ["wip"]
    assert {(i["kind"], i["item_id"]) for i in study["items"]} == {
        ("experiment", experiment),
        ("batch", batch),
    }


def test_a_study_refuses_items_that_do_not_exist(client, engine):
    experiment = make_experiment(engine)

    response = client.post(
        "/studies",
        json={"name": "x", "items": [ref("experiment", experiment), ref("batch", 999)]},
    )

    assert response.status_code == 422
    assert client.get("/studies").json() == []


def test_update_renames_describes_and_changes_the_status(client):
    study = make_study(client, description="old")

    response = client.put(
        f"/studies/{study['id']}",
        json={"name": " Better ", "description": None, "status": "concluded"},
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["name"], body["description"], body["status"]) == (
        "Better",
        None,
        "concluded",
    )


def test_update_leaves_the_description_alone_when_it_is_not_sent(client):
    study = make_study(client, description="keep me")

    body = client.put(f"/studies/{study['id']}", json={"name": "Renamed"}).json()

    assert body["description"] == "keep me"


def test_update_replaces_the_tags(client):
    study = make_study(client)
    red = client.post("/tags", json={"name": "red"}).json()
    blue = client.post("/tags", json={"name": "blue"}).json()
    client.put(f"/studies/{study['id']}", json={"tag_ids": [red["id"]]})

    body = client.put(f"/studies/{study['id']}", json={"tag_ids": [blue["id"]]}).json()

    assert [t["name"] for t in body["tags"]] == ["blue"]


def test_an_archived_study_is_read_only_until_it_is_brought_back(client, engine):
    experiment = make_experiment(engine)
    study = make_study(client)
    sid = study["id"]
    assert client.put(f"/studies/{sid}", json={"status": "archived"}).status_code == 200

    assert client.put(f"/studies/{sid}", json={"name": "x"}).status_code == 409
    assert client.put(f"/studies/{sid}", json={"status": "archived"}).status_code == 409
    add = client.post(
        f"/studies/{sid}/items", json={"items": [ref("experiment", experiment)]}
    )
    assert add.status_code == 409

    back = client.put(f"/studies/{sid}", json={"status": "active", "name": "Back"})
    assert back.status_code == 200
    assert back.json()["name"] == "Back"


def test_an_unknown_study_is_not_found(client):
    assert client.get("/studies/999").status_code == 404
    assert client.put("/studies/999", json={"name": "x"}).status_code == 404
    assert client.delete("/studies/999").status_code == 404


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


def test_an_item_can_be_in_several_studies(client, engine):
    experiment = make_experiment(engine)
    first = make_study(client, "A", items=[ref("experiment", experiment)])
    second = make_study(client, "B", items=[ref("experiment", experiment)])

    memberships = client.get(
        "/studies/memberships", params={"kind": "experiment"}
    ).json()

    assert memberships == [
        {"study_id": first["id"], "item_id": experiment},
        {"study_id": second["id"], "item_id": experiment},
    ]
    assert client.get("/studies/memberships", params={"kind": "batch"}).json() == []


def test_adding_an_item_twice_keeps_one_link(client, engine):
    experiment = make_experiment(engine)
    study = make_study(client)
    path = f"/studies/{study['id']}/items"

    client.post(path, json={"items": [ref("experiment", experiment)]})
    body = client.post(path, json={"items": [ref("experiment", experiment)]}).json()

    assert body["counts"]["experiments"] == 1
    assert len(body["items"]) == 1


def test_an_item_is_taken_out_without_being_deleted(client, engine):
    experiment = make_experiment(engine)
    study = make_study(client, items=[ref("experiment", experiment)])
    path = f"/studies/{study['id']}/items/experiment/{experiment}"

    assert client.delete(path).status_code == 204
    assert client.get(f"/studies/{study['id']}").json()["items"] == []
    assert client.get(f"/experiments/{experiment}").status_code == 200
    assert client.delete(path).status_code == 404


def test_the_items_say_what_they_are(client, engine):
    batch = make_batch(engine, "Grid")
    make_experiment(engine, "cell 1", batch_id=batch, executions=[(100, 0.5)])
    make_experiment(engine, "cell 2", batch_id=batch, status="failed")
    solo = make_experiment(engine, "Solo", executions=[(10, 0.1), (20, 0.2)])
    analysis = make_analysis(engine)
    study = make_study(
        client,
        items=[ref("batch", batch), ref("experiment", solo), ref("analysis", analysis)],
    )

    items = {i["kind"]: i for i in study["items"]}

    assert items["batch"]["name"] == "Grid"
    assert items["batch"]["status"] == "partial"
    assert items["batch"]["experiment_count"] == 2
    assert items["batch"]["dataset_name"] == "answers"
    assert items["experiment"]["status"] == "completed"
    # The latest execution is the one that counts, earlier ones are only counted
    assert items["experiment"]["total_tokens"] == 20
    assert items["experiment"]["execution_count"] == 2
    assert items["analysis"]["name"] == "Agreement"
    assert items["analysis"]["status"] is None


def test_the_totals_count_each_experiment_once(client, engine):
    batch = make_batch(engine)
    inside = make_experiment(
        engine, "in batch", batch_id=batch, executions=[(100, 1.0)]
    )
    solo = make_experiment(engine, "solo", executions=[(50, 0.5)])

    study = make_study(
        client,
        items=[
            ref("batch", batch),
            # Already counted through its batch
            ref("experiment", inside),
            ref("experiment", solo),
        ],
    )

    assert study["counts"] == {"experiments": 2, "batches": 1, "analyses": 0}
    assert study["execution_count"] == 2
    assert study["total_tokens"] == 150
    assert study["total_cost_usd"] == pytest.approx(1.5)


def test_a_study_without_any_figure_has_no_totals(client, engine):
    experiment = make_experiment(engine, status="pending")

    study = make_study(client, items=[ref("experiment", experiment)])

    assert study["execution_count"] == 0
    assert study["total_tokens"] is None
    assert study["total_cost_usd"] is None


def test_assign_puts_selected_items_in_and_out_of_studies(client, engine):
    first, second = make_experiment(engine, "one"), make_experiment(engine, "two")
    a, b = make_study(client, "A"), make_study(client, "B")
    client.post(f"/studies/{b['id']}/items", json={"items": [ref("experiment", first)]})

    response = client.post(
        "/studies/assign",
        json={
            "kind": "experiment",
            "item_ids": [first, second],
            "add": [a["id"]],
            "remove": [b["id"]],
        },
    )

    assert response.status_code == 204
    memberships = client.get(
        "/studies/memberships", params={"kind": "experiment"}
    ).json()
    assert memberships == [
        {"study_id": a["id"], "item_id": first},
        {"study_id": a["id"], "item_id": second},
    ]


def test_assign_refuses_unknown_items_and_studies_and_archived_ones(client, engine):
    experiment = make_experiment(engine)
    study = make_study(client)
    body = {"kind": "experiment", "item_ids": [experiment], "add": [study["id"]]}

    assert (
        client.post("/studies/assign", json={**body, "item_ids": [999]}).status_code
        == 422
    )
    assert (
        client.post("/studies/assign", json={**body, "add": [999]}).status_code == 422
    )

    client.put(f"/studies/{study['id']}", json={"status": "archived"})
    assert client.post("/studies/assign", json=body).status_code == 409
    assert (
        client.get("/studies/memberships", params={"kind": "experiment"}).json() == []
    )


def test_assign_adds_without_duplicating(client, engine):
    experiment = make_experiment(engine)
    study = make_study(client, items=[ref("experiment", experiment)])
    body = {"kind": "experiment", "item_ids": [experiment], "add": [study["id"]]}

    assert client.post("/studies/assign", json=body).status_code == 204

    assert client.get(f"/studies/{study['id']}").json()["counts"]["experiments"] == 1


def test_the_list_puts_the_most_recently_touched_study_first(client, engine):
    old, new = make_study(client, "old"), make_study(client, "new")
    experiment = make_experiment(engine)

    assert [s["name"] for s in client.get("/studies").json()] == ["new", "old"]
    client.post(
        f"/studies/{old['id']}/items", json={"items": [ref("experiment", experiment)]}
    )

    assert [s["name"] for s in client.get("/studies").json()] == ["old", "new"]
    assert client.get("/studies").json()[0]["id"] == old["id"]
    assert new["id"] != old["id"]


# ---------------------------------------------------------------------------
# Deleting
# ---------------------------------------------------------------------------


def test_deleting_a_study_leaves_what_it_gathered_alone(client, engine, alice):
    experiment = make_experiment(engine)
    batch = make_batch(engine)
    tag = client.post("/tags", json={"name": "wip"}).json()
    study = make_study(
        client,
        items=[ref("experiment", experiment), ref("batch", batch)],
        tag_ids=[tag["id"]],
    )
    client.post(
        "/notes",
        json={"kind": "study", "item_id": study["id"], "body": "about the study"},
    )
    client.post(
        "/notes",
        json={"kind": "experiment", "item_id": experiment, "body": "about the run"},
    )

    assert client.delete(f"/studies/{study['id']}").status_code == 204

    assert client.get(f"/experiments/{experiment}").status_code == 200
    assert client.get(f"/batches/{batch}").status_code == 200
    with scoped(engine) as s:
        assert s.exec(select(StudyItem)).all() == []
        assert s.exec(select(TagLink).where(TagLink.kind == "study")).all() == []
        remaining = s.exec(select(Note)).all()
    assert [(n.kind, n.body) for n in remaining] == [("experiment", "about the run")]


def test_deleting_an_item_takes_it_out_of_its_studies_with_its_notes(
    client, engine, alice
):
    experiment = make_experiment(engine)
    batch = make_batch(engine)
    analysis = make_analysis(engine)
    study = make_study(
        client,
        items=[
            ref("experiment", experiment),
            ref("batch", batch),
            ref("analysis", analysis),
        ],
    )
    for kind, item in (
        ("experiment", experiment),
        ("batch", batch),
        ("analysis", analysis),
    ):
        client.post(
            "/notes", json={"kind": kind, "item_id": item, "body": f"on the {kind}"}
        )
    client.post(
        "/notes", json={"kind": "study", "item_id": study["id"], "body": "kept"}
    )

    assert client.delete(f"/experiments/{experiment}").status_code == 204
    assert client.delete(f"/batches/{batch}").status_code == 204
    assert client.delete(f"/analyses/{analysis}").status_code == 204

    body = client.get(f"/studies/{study['id']}").json()
    assert body["items"] == []
    assert body["counts"] == {"experiments": 0, "batches": 0, "analyses": 0}
    with scoped(engine) as s:
        assert [n.body for n in s.exec(select(Note)).all()] == ["kept"]


def test_deleting_a_batch_keeps_its_experiments_in_the_study_when_they_were_put_there(
    client, engine
):
    batch = make_batch(engine)
    inside = make_experiment(engine, batch_id=batch)
    study = make_study(client, items=[ref("batch", batch), ref("experiment", inside)])

    client.delete(f"/batches/{batch}")

    body = client.get(f"/studies/{study['id']}").json()
    assert [(i["kind"], i["item_id"]) for i in body["items"]] == [
        ("experiment", inside)
    ]


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------


def test_the_activity_tells_what_happened_newest_first(client, engine, alice):
    batch = make_batch(engine, "Grid")
    make_experiment(engine, "cell", batch_id=batch)
    solo = make_experiment(engine, "Solo", status="running")
    study = make_study(
        client, "Prompt v3", items=[ref("batch", batch), ref("experiment", solo)]
    )
    sid = study["id"]
    client.post(
        "/notes", json={"kind": "experiment", "item_id": solo, "body": "slow run"}
    )
    client.post("/notes", json={"kind": "study", "item_id": sid, "body": "# Findings"})

    events = client.get(f"/studies/{sid}/activity").json()

    kinds = [(e["type"], e["item"]["kind"], e["item"]["name"]) for e in events]
    # The experiment of the batch finished before the study was made
    assert kinds[0] == ("note", "study", "Prompt v3")
    assert kinds[1] == ("note", "experiment", "Solo")
    assert set(kinds[2:]) == {
        ("item_added", "batch", "Grid"),
        ("item_added", "experiment", "Solo"),
        ("experiment_completed", "experiment", "cell"),
    }
    note = events[0]["note"]
    assert note["body"] == "# Findings"
    assert note["author"]["display_name"] == "Alice"
    assert [e["at"] for e in events] == sorted((e["at"] for e in events), reverse=True)


def test_an_item_taken_out_leaves_the_timeline_with_its_notes(client, engine, alice):
    experiment = make_experiment(engine, "Run")
    study = make_study(client, items=[ref("experiment", experiment)])
    client.post(
        "/notes", json={"kind": "experiment", "item_id": experiment, "body": "x"}
    )
    client.delete(f"/studies/{study['id']}/items/experiment/{experiment}")

    assert client.get(f"/studies/{study['id']}/activity").json() == []


def test_the_activity_is_cut_to_the_limit(client, engine, alice):
    study = make_study(client)
    for n in range(5):
        client.post(
            "/notes", json={"kind": "study", "item_id": study["id"], "body": f"n{n}"}
        )

    events = client.get(f"/studies/{study['id']}/activity", params={"limit": 3}).json()

    assert [e["note"]["body"] for e in events] == ["n4", "n3", "n2"]
