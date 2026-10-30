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

"""Public links: who makes them, what they open, and what they never show."""

import json

import pytest
from sqlmodel import Session, select

import config
import main
from api import shared
from tables import Experiment, Share
from tests.shares.conftest import build_world, share, workspace_id
from workspace_scope import scope_session

# What a link must not carry: people, tags, files of the server, notes, the workspace
FORBIDDEN_TEXT = ("Alice", "Team", "secret-wip", "private/answers.csv", "rows.json", "PRIVATE NOTE", '"Base"')


def walk(value):
    """Every (key, value) pair of a JSON document."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def reachable(reader, token, path):
    return reader.get(f"/shared/{token}{path}").status_code == 200


# ---------------------------------------------------------------------------
# Making and withdrawing links
# ---------------------------------------------------------------------------


def test_editors_make_links_and_viewers_cannot(alice, bob, carol, team, engine):
    world = build_world(engine, team, alice.id)
    url = f"/workspaces/{team}/shares"
    body = {"kind": "experiment", "item_id": world["solo"]}

    assert carol.post(url, json=body).status_code == 403
    assert carol.get(url, params={"kind": "experiment", "item_id": world["solo"]}).status_code == 403

    made = bob.post(url, json=body)
    assert made.status_code == 201
    token = made.json()["token"]
    assert len(token) >= 21

    # The same item gets the same link, and the editor can see it again
    again = alice.post(url, json=body)
    assert again.status_code == 200
    assert again.json()["token"] == token
    seen = bob.get(url, params={"kind": "experiment", "item_id": world["solo"]})
    assert seen.json()["token"] == token
    assert bob.get(url, params={"kind": "experiment", "item_id": world["other"]}).json() is None

    missing = bob.post(url, json={"kind": "experiment", "item_id": 99999})
    assert missing.status_code == 404
    assert carol.delete(f"{url}/{made.json()['id']}").status_code == 403


def test_a_withdrawn_link_is_gone_and_the_next_one_is_new(alice, team, engine, reader):
    world = build_world(engine, team, alice.id)
    url = f"/workspaces/{team}/shares"
    made = alice.post(url, json={"kind": "experiment", "item_id": world["solo"]}).json()
    assert reachable(reader, made["token"], f"/experiments/{world['solo']}")

    assert alice.delete(f"{url}/{made['id']}").status_code == 204
    assert alice.delete(f"{url}/{made['id']}").status_code == 204
    assert reader.get(f"/shared/{made['token']}").status_code == 410
    assert reader.get("/shared/not-a-link").status_code == 404

    fresh = alice.post(url, json={"kind": "experiment", "item_id": world["solo"]})
    assert fresh.status_code == 201
    assert fresh.json()["token"] != made["token"]
    assert reachable(reader, fresh.json()["token"], f"/experiments/{world['solo']}")
    assert reader.get(f"/shared/{made['token']}").status_code == 410


def test_deleting_an_item_takes_its_link_away(alice, team, engine, reader):
    world = build_world(engine, team, alice.id)
    base = f"/workspaces/{team}"
    tokens = {
        "experiment": share(alice, team, "experiment", world["other"]),
        "study": share(alice, team, "study", world["study"]),
    }

    assert alice.delete(f"{base}/experiments/{world['other']}").status_code == 204
    assert alice.delete(f"{base}/studies/{world['study']}").status_code == 204

    for token in tokens.values():
        assert reader.get(f"/shared/{token}").status_code == 404
    with Session(engine) as db:
        assert db.exec(select(Share)).all() == []


def test_an_archived_workspace_keeps_its_links_and_lets_them_be_withdrawn(alice, team, engine, reader):
    world = build_world(engine, team, alice.id)
    base = f"/workspaces/{team}"
    made = alice.post(
        f"{base}/shares", json={"kind": "experiment", "item_id": world["solo"]}
    ).json()
    assert alice.post(f"{base}/archive").status_code in (200, 204)

    assert reachable(reader, made["token"], f"/experiments/{world['solo']}")
    seen = alice.get(f"{base}/shares", params={"kind": "experiment", "item_id": world["solo"]})
    assert seen.json()["token"] == made["token"]
    other = {"kind": "experiment", "item_id": world["other"]}
    # Nothing new is exposed, but an exposure can always be stopped
    assert alice.post(f"{base}/shares", json=other).status_code == 409
    assert alice.delete(f"{base}/shares/{made['id']}").status_code == 204
    assert reader.get(f"/shared/{made['token']}").status_code == 410


def test_an_instance_can_turn_sharing_off(alice, team, engine, reader, monkeypatch):
    world = build_world(engine, team, alice.id)
    base = f"/workspaces/{team}"
    made = alice.post(
        f"{base}/shares", json={"kind": "experiment", "item_id": world["solo"]}
    ).json()
    assert alice.get("/auth/me").json()["public_sharing"] is True

    monkeypatch.setattr(config, "PUBLIC_SHARING_ENABLED", False)

    assert alice.get("/auth/me").json()["public_sharing"] is False
    body = {"kind": "experiment", "item_id": world["other"]}
    assert alice.post(f"{base}/shares", json=body).status_code == 403
    assert reader.get(f"/shared/{made['token']}").status_code == 404
    # A link can still be withdrawn, so that it does not come back to life
    assert alice.delete(f"{base}/shares/{made['id']}").status_code == 204


# ---------------------------------------------------------------------------
# What a link opens
# ---------------------------------------------------------------------------


def test_a_link_to_an_experiment_opens_it_and_its_executions(alice, team, engine, reader):
    world = build_world(engine, team, alice.id)
    token = share(alice, team, "experiment", world["solo"])

    root = reader.get(f"/shared/{token}")
    assert root.json() == {"kind": "experiment", "item_id": world["solo"], "name": "Solo"}
    for path in (
        f"/experiments/{world['solo']}",
        f"/experiments/{world['solo']}/executions",
        f"/executions/{world['solo_run']}",
        f"/executions/{world['solo_run']}/results",
        f"/executions/{world['solo_run']}/rows/1",
        f"/executions/{world['solo_run']}/analysis-fields",
        "/analyses/metrics",
    ):
        assert reachable(reader, token, path), path

    for path in (
        f"/experiments/{world['other']}",
        f"/experiments/{world['other']}/executions",
        f"/executions/{world['other_run']}",
        f"/executions/{world['other_run']}/rows/1",
        f"/analyses/{world['analysis']}",
        f"/batches/{world['batch']}",
        f"/studies/{world['study']}",
        "/experiments/not-a-number",
    ):
        assert reader.get(f"/shared/{token}{path}").status_code == 404, path


def test_a_link_to_a_batch_opens_its_experiments_but_not_where_it_came_from(
    alice, team, engine, reader
):
    world = build_world(engine, team, alice.id)
    token = share(alice, team, "batch", world["batch"])

    for path in (
        f"/batches/{world['batch']}",
        f"/experiments/{world['member']}",
        f"/executions/{world['member_run']}",
    ):
        assert reachable(reader, token, path), path
    assert reader.get(f"/shared/{token}/experiments/{world['base']}").status_code == 404
    assert reader.get(f"/shared/{token}/experiments/{world['solo']}").status_code == 404


def test_a_link_to_an_analysis_opens_the_runs_it_compares_and_nothing_else(
    alice, team, engine, reader
):
    world = build_world(engine, team, alice.id)
    token = share(alice, team, "analysis", world["analysis"])

    assert reachable(reader, token, f"/analyses/{world['analysis']}")
    assert reachable(reader, token, f"/analyses/{world['analysis']}/results")
    assert reachable(reader, token, f"/executions/{world['solo_run']}/rows/1")
    # The experiment of a compared run is not part of the analysis
    assert reader.get(f"/shared/{token}/experiments/{world['solo']}").status_code == 404
    assert reader.get(f"/shared/{token}/executions/{world['other_run']}").status_code == 404


def test_a_link_to_a_study_opens_what_it_gathers(alice, team, engine, reader):
    world = build_world(engine, team, alice.id)
    token = share(alice, team, "study", world["study"])

    for path in (
        f"/studies/{world['study']}",
        f"/batches/{world['batch']}",
        f"/experiments/{world['member']}",
        f"/analyses/{world['analysis']}",
        f"/executions/{world['member_run']}",
        f"/executions/{world['solo_run']}",
    ):
        assert reachable(reader, token, path), path
    # What the study does not gather stays closed, and so does what a batch came from
    for path in (
        f"/experiments/{world['solo']}",
        f"/experiments/{world['other']}",
        f"/experiments/{world['base']}",
    ):
        assert reader.get(f"/shared/{token}{path}").status_code == 404, path


def test_a_link_stays_in_its_workspace(alice, bob, engine, team, reader):
    world = build_world(engine, team, alice.id)
    elsewhere = bob.create_workspace("Elsewhere")
    with Session(engine) as db:
        scope_session(db, workspace_id(engine, elsewhere))
        foreign = Experiment(name="Foreign", dataset_id=1)
        # A dataset of its own, so the foreign experiment is complete
        from tables import Dataset

        dataset = Dataset(name="theirs", file_path="theirs.csv")
        db.add(dataset)
        db.flush()
        foreign.dataset_id = dataset.id
        db.add(foreign)
        db.commit()
        foreign_id = foreign.id

    token = share(alice, team, "study", world["study"])

    assert reader.get(f"/shared/{token}/experiments/{foreign_id}").status_code == 404
    # Its owner cannot make a link to it either
    body = {"kind": "experiment", "item_id": foreign_id}
    assert alice.post(f"/workspaces/{team}/shares", json=body).status_code == 404


# ---------------------------------------------------------------------------
# What a link never shows
# ---------------------------------------------------------------------------


def test_only_the_reading_routes_are_there(alice, team, engine, reader):
    world = build_world(engine, team, alice.id)
    token = share(alice, team, "study", world["study"])

    mounted = {
        route.path.removeprefix("/shared/{token}")
        for route in main.app.routes
        if route.path.startswith("/shared/")
    }
    assert mounted == shared.READABLE | {""}
    assert all(
        route.methods == {"GET"}
        for route in main.app.routes
        if route.path.startswith("/shared/")
    )

    for path in ("/experiments", "/notes", "/models", "/datasets/1", "/tags", "/studies"):
        assert reader.get(f"/shared/{token}{path}").status_code in (404, 405), path
    wrote = reader.post(f"/shared/{token}/experiments/{world['member']}/rerun")
    assert wrote.status_code in (404, 405)
    assert reader.delete(f"/shared/{token}/studies/{world['study']}").status_code == 405
    # The workspace's own routes still want an account
    assert reader.get(f"/workspaces/{team}/experiments").status_code == 401


def test_a_link_hides_people_tags_notes_and_files_of_the_server(alice, team, engine, reader):
    world = build_world(engine, team, alice.id)
    token = share(alice, team, "study", world["study"])
    # What the app itself shows, so that the test fails if the link ever shows the same
    assert "Alice" in json.dumps(
        alice.get(f"/workspaces/{team}/studies/{world['study']}").json()
    )

    documents = []
    for path in (
        f"/studies/{world['study']}",
        f"/batches/{world['batch']}",
        f"/experiments/{world['member']}",
        f"/experiments/{world['member']}/executions",
        f"/executions/{world['member_run']}",
        f"/analyses/{world['analysis']}",
    ):
        response = reader.get(f"/shared/{token}{path}")
        assert response.status_code == 200, path
        documents.append(response.json())

    for document in documents:
        text = json.dumps(document)
        for forbidden in FORBIDDEN_TEXT:
            assert forbidden not in text, forbidden
        for key, value in walk(document):
            if key in (
                "author",
                "added_by",
                "launched_by",
                "file_path",
                "base_experiment_id",
                "base_experiment_name",
            ):
                assert value is None, key
            if key == "results_file_path":
                # Only that there is a file, not where it is
                assert value in (None, "results.json")
            if key == "tags":
                assert value == []
    # The study still says what it is about
    assert documents[0]["description"] == "Why we did it"


def test_a_link_does_not_name_a_batch_it_does_not_reach(alice, team, engine, reader):
    world = build_world(engine, team, alice.id)
    alone = share(alice, team, "experiment", world["member"])
    with_batch = share(alice, team, "batch", world["batch"])

    hidden = reader.get(f"/shared/{alone}/experiments/{world['member']}").json()
    shown = reader.get(f"/shared/{with_batch}/experiments/{world['member']}").json()

    assert hidden["batch_name"] is None
    assert shown["batch_name"] == "Grid"


def test_the_results_of_an_analysis_do_not_name_the_experiments_it_compares(
    alice, team, engine, reader
):
    world = build_world(engine, team, alice.id)
    token = share(alice, team, "analysis", world["analysis"])

    runs = reader.get(f"/shared/{token}/analyses/{world['analysis']}/results").json()["runs"]

    assert runs
    for run in runs:
        assert run["experiment_id"] is None
        assert run["experiment_name"] is None


def test_what_a_dataset_holds_is_shown_as_it_is(alice, team, engine, reader):
    world = build_world(engine, team, alice.id)
    token = share(alice, team, "experiment", world["solo"])

    row = reader.get(f"/shared/{token}/executions/{world['solo_run']}/rows/1").json()

    # A column called "author" or "file_path" is data, not what the app hides
    assert row["input_data"] == {
        "text": "great",
        "author": "Dr Who",
        "file_path": "x.csv",
        "score": 5,
    }


def test_a_download_is_named_after_its_execution_not_its_experiment(alice, team, engine, reader):
    world = build_world(engine, team, alice.id)
    token = share(alice, team, "analysis", world["analysis"])

    download = reader.get(f"/shared/{token}/executions/{world['solo_run']}/results")

    assert download.status_code == 200
    disposition = download.headers["content-disposition"]
    assert f"execution_{world['solo_run']}_results.json" in disposition
    assert "Solo" not in disposition


def test_what_cannot_be_a_token_or_an_id_is_a_plain_404(alice, team, engine, reader):
    world = build_world(engine, team, alice.id)
    token = share(alice, team, "experiment", world["solo"])

    for bad in ("%00", "a" * 200, "x y", "..%2F.."):
        assert reader.get(f"/shared/{bad}").status_code == 404, bad
    for bad in ("9" * 5000, "٣", "-1", "1.5"):
        assert reader.get(f"/shared/{token}/experiments/{bad}").status_code == 404, bad


def test_a_link_asks_browsers_and_crawlers_to_forget_it(alice, team, engine, reader):
    world = build_world(engine, team, alice.id)
    token = share(alice, team, "experiment", world["solo"])

    for path in ("", f"/experiments/{world['solo']}", "/experiments/99999"):
        response = reader.get(f"/shared/{token}{path}")
        assert response.headers["x-robots-tag"] == "noindex, nofollow"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["cache-control"] == "private, no-cache"
    assert "x-robots-tag" not in reader.get("/health").headers


@pytest.mark.parametrize("kind", ["experiment", "batch", "analysis", "study"])
def test_every_kind_can_be_shared(alice, team, engine, reader, kind):
    world = build_world(engine, team, alice.id)
    token = share(alice, team, kind, world["solo" if kind == "experiment" else kind])

    assert reader.get(f"/shared/{token}").json()["kind"] == kind
