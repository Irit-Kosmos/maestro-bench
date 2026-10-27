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
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import prompts


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(prompts.router)
    return TestClient(app)


def render(client, **body):
    return client.post("/prompts/render", json=body)


def test_renders_both_prompts_with_the_values(client):
    response = render(
        client,
        system_prompt="You grade {{ topic }}.",
        user_prompt="Answer: {{ answer }}",
        variables={"topic": "French", "answer": "Bonjour"},
    )
    assert response.status_code == 200
    assert response.json() == {"system": "You grade French.", "user": "Answer: Bonjour"}


def test_renders_the_legacy_slots_like_a_run_does(client):
    response = render(
        client,
        user_prompt="<answer></answer>",
        variables={"answer": "Bonjour"},
    )
    assert response.json()["user"] == "<answer>Bonjour</answer>"


def test_a_missing_variable_renders_empty_and_a_missing_prompt_is_empty(client):
    response = render(client, user_prompt="[{{ nope }}]")
    assert response.json() == {"system": "", "user": "[]"}


def test_a_template_reaching_for_the_interpreter_is_refused(client):
    response = render(
        client,
        user_prompt="{{ ''.__class__.__mro__[1].__subclasses__() }}",
    )
    assert response.status_code == 422
