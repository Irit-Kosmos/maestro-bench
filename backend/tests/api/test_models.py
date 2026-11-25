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

"""A model's default temperature, and models that take none."""

import pytest

from api import models
from tests.conftest import api_client


@pytest.fixture
def client(engine):
    return api_client(engine, models)


def create(client, **fields):
    response = client.post("/models", json={"name": "m", "provider": "openai", **fields})
    assert response.status_code == 201
    return response.json()


class TestTemperature:
    def test_left_empty_stays_empty(self, client):
        model = create(client)

        assert model["default_temperature"] is None
        assert model["supports_temperature"] is True

    def test_a_model_without_temperature_keeps_no_default(self, client):
        model = create(client, supports_temperature=False, default_temperature=0.5)

        assert model["default_temperature"] is None

    def test_turning_it_off_clears_the_default(self, client):
        model = create(client, default_temperature=0.5)

        updated = client.put(
            f"/models/{model['id']}", json={"supports_temperature": False}
        ).json()

        assert updated["supports_temperature"] is False
        assert updated["default_temperature"] is None

    def test_edit_can_clear_the_default(self, client):
        model = create(client, default_temperature=0.5)

        updated = client.put(
            f"/models/{model['id']}", json={"default_temperature": None}
        ).json()

        assert updated["default_temperature"] is None
