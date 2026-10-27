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

"""Signed-in people to drive the real application with, one browser each."""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

import config
import main
from auth.policy import Profile
from auth.sessions import create_session
from auth.users import sign_in
from auth.workspaces import set_member
from tables import User, Workspace


class Person:
    """A signed-in user with their own browser."""

    def __init__(self, engine, name: str):
        self.email = f"{name}@irit.fr"
        with Session(engine) as db:
            self.user = sign_in(
                db,
                Profile(
                    provider="gitlab",
                    subject=name,
                    display_name=name.title(),
                    email=self.email,
                ),
            )
            self.id = self.user.id
            token = create_session(db, self.id)
        self.client = TestClient(main.app)
        self.client.cookies.set(config.SESSION_COOKIE_NAME, token)
        self.csrf = self.client.get("/auth/me").json()["csrf_token"]

    def get(self, url, **kwargs):
        return self.client.get(url, **kwargs)

    def _write(self, method, url, **kwargs):
        headers = {"X-CSRF-Token": self.csrf, **kwargs.pop("headers", {})}
        return self.client.request(method, url, headers=headers, **kwargs)

    def post(self, url, **kwargs):
        return self._write("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self._write("PUT", url, **kwargs)

    def patch(self, url, **kwargs):
        return self._write("PATCH", url, **kwargs)

    def delete(self, url, **kwargs):
        return self._write("DELETE", url, **kwargs)

    def create_workspace(self, name: str) -> str:
        response = self.post("/workspaces", json={"name": name})
        assert response.status_code == 201, response.text
        return response.json()["slug"]


def add_member(engine, slug: str, person: Person, role: str) -> None:
    with Session(engine) as db:
        workspace = db.exec(select(Workspace).where(Workspace.slug == slug)).one()
        set_member(db, workspace, db.get(User, person.id), role)
