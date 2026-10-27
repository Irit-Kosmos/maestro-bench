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

import pytest
from sqlmodel import Session

import config
import main
from auth.deps import get_engine
from db import get_session
from tests.auth.people import Person


@pytest.fixture(autouse=True)
def auth_config(monkeypatch):
    """A known set of authentication settings, whatever the environment says."""
    settings = {
        "SECRET_KEY": "k" * 48,
        "FRONTEND_URL": "http://localhost:3000",
        "CORS_ORIGINS": ["http://localhost:3000"],
        "PUBLIC_API_URL": "http://localhost:8000",
        "COOKIE_SECURE": False,
        "SESSION_IDLE_DAYS": 7,
        "SESSION_MAX_DAYS": 30,
        "AUTH_ALLOWED_EMAIL_DOMAINS": ["irit.fr"],
        "AUTH_GITLAB_ALLOWED_GROUPS": [],
        "AUTH_ALLOW_ANY_USER": False,
        "INSTANCE_ADMINS": [],
    }
    for name, value in settings.items():
        monkeypatch.setattr(config, name, value)


@pytest.fixture
def app(engine):
    def _session():
        with Session(engine) as session:
            yield session

    main.app.dependency_overrides[get_session] = _session
    main.app.dependency_overrides[get_engine] = lambda: engine
    yield main.app
    main.app.dependency_overrides.clear()


@pytest.fixture
def alice(engine, app):
    return Person(engine, "alice")


@pytest.fixture
def bob(engine, app):
    return Person(engine, "bob")
