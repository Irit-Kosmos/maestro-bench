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

import credentials
from api import setup
from tables import Agent, Dataset, Experiment, Model, Prompt, PromptVersion
from tests.conftest import api_client, scoped


@pytest.fixture
def client(engine, monkeypatch):
    # No key on the machine running the tests
    monkeypatch.setattr(credentials, "instance_provides", lambda provider: False)
    return api_client(engine, setup)


def progress(client) -> dict[str, bool]:
    response = client.get("/setup")
    assert response.status_code == 200
    return response.json()


def test_an_empty_workspace_has_taken_no_step(client):
    assert progress(client) == {
        "provider": False,
        "dataset": False,
        "prompt": False,
        "model": False,
        "agent": False,
        "experiment": False,
    }


def test_each_step_is_ticked_by_what_the_workspace_holds(client, engine):
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        model = Model(name="m", provider="openai")
        prompt = Prompt(name="Grader")
        s.add_all([dataset, model, prompt])
        s.flush()
        s.add(PromptVersion(prompt_id=prompt.id, version="1"))
        s.add(Agent(name="a"))
        s.commit()

    assert progress(client) == {
        "provider": False,
        "dataset": True,
        # The prompt counts once it has a version
        "prompt": True,
        "model": True,
        "agent": True,
        "experiment": False,
    }

    with scoped(engine) as s:
        s.add(Experiment(name="run", dataset_id=1))
        s.commit()
    assert progress(client)["experiment"] is True


def test_a_prompt_without_a_version_is_not_a_step_done(client, engine):
    with scoped(engine) as s:
        s.add(Prompt(name="Grader"))
        s.commit()

    assert progress(client)["prompt"] is False


def test_a_key_of_the_instance_counts_as_a_provider(client, monkeypatch):
    monkeypatch.setattr(credentials, "instance_provides", lambda provider: provider == "openai")

    assert progress(client)["provider"] is True
