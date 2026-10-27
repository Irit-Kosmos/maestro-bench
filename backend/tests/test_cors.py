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
from fastapi.testclient import TestClient

import main
from config import CORS_ORIGINS

ORIGIN = CORS_ORIGINS[0]


@pytest.fixture
def client():
    return TestClient(main.app)


def preflight(client, method: str, headers: str, origin: str = ORIGIN):
    return client.options(
        "/workspaces/x/experiments",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )


def test_the_interface_may_use_its_methods(client):
    for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        response = preflight(client, method, "Content-Type, X-CSRF-Token")

        assert response.status_code == 200, method
        assert response.headers["access-control-allow-origin"] == ORIGIN
        assert response.headers["access-control-allow-credentials"] == "true"


def test_a_header_the_interface_never_sends_is_refused(client):
    assert preflight(client, "POST", "X-Something-Else").status_code == 400


def test_a_method_the_interface_never_uses_is_refused(client):
    assert preflight(client, "TRACE", "Content-Type").status_code == 400


def test_another_origin_is_refused(client):
    response = preflight(client, "GET", "Content-Type", origin="https://evil.example")

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
