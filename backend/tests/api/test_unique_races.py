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

"""Two requests can pass the same availability check: the unique index decides, and
the loser gets an answer, not a server error."""

import pytest
from sqlmodel import Session, select

from api import tags
from auth import workspaces
from tables import User, Workspace
from tests.conftest import api_client


@pytest.fixture
def client(engine):
    return api_client(engine, tags)


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
