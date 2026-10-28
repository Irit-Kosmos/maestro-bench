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

"""Who made what: the lists and pages name the author of each item."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from api import (
    agents,
    analyses,
    batches,
    datasets,
    experiment_executions,
    experiments,
    prompts,
)
from db import get_session
from tables import (
    Analysis,
    Batch,
    Dataset,
    Experiment,
    ExperimentExecution,
    User,
)
from tests.conftest import TEST_WORKSPACE_ID, scoped
from workspace_scope import scope_session


def make_user(engine, name):
    with Session(engine, expire_on_commit=False) as db:
        user = User(display_name=name)
        db.add(user)
        db.commit()
        return user


@pytest.fixture
def alice(engine):
    return make_user(engine, "Alice")


@pytest.fixture
def bob(engine):
    return make_user(engine, "Bob")


@pytest.fixture
def client(engine, alice):
    """Requests made by Alice."""
    app = FastAPI()
    for module in (
        agents,
        analyses,
        batches,
        datasets,
        experiment_executions,
        experiments,
        prompts,
    ):
        app.include_router(module.router)

    def _session():
        with Session(engine) as session:
            scope_session(session, TEST_WORKSPACE_ID, alice.id)
            yield session

    app.dependency_overrides[get_session] = _session
    return TestClient(app)


def author_name(item):
    return item["author"]["display_name"] if item["author"] else None


def test_what_is_created_names_its_author(client):
    prompt = client.post("/prompts", json={"name": "Grader"}).json()
    version = client.post(
        f"/prompts/{prompt['id']}/versions", json={"version": "1", "user_prompt": "x"}
    ).json()
    agent = client.post("/agents", json={"name": "Grader"}).json()
    dataset = client.post("/datasets", json={"name": "answers"}).json()

    assert author_name(prompt) == "Alice"
    assert author_name(version) == "Alice"
    assert author_name(agent) == "Alice"
    assert author_name(dataset) == "Alice"
    # And so do the lists and pages that read them again
    assert author_name(client.get(f"/prompts/{prompt['id']}").json()) == "Alice"
    assert [author_name(v) for v in client.get(f"/prompts/{prompt['id']}/versions").json()] == ["Alice"]
    assert author_name(client.get(f"/prompt-versions/{version['id']}").json()) == "Alice"
    assert [author_name(v) for v in client.get("/prompt-versions").json()] == ["Alice"]
    assert [author_name(a) for a in client.get("/agents").json()] == ["Alice"]
    assert [author_name(d) for d in client.get("/datasets").json()] == ["Alice"]


def test_items_name_who_made_them_and_nobody_when_it_is_unknown(engine, client, bob):
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        s.add(dataset)
        s.flush()
        made_by_bob = Experiment(name="Bob's", dataset_id=dataset.id, created_by=bob.id)
        # Made before authors were kept
        unknown = Experiment(name="Old", dataset_id=dataset.id)
        batch = Batch(name="Grid", created_by=bob.id)
        analysis = Analysis(
            name="Agreement",
            config=json.dumps({"truth_column": "t", "value_type": "numeric", "metrics": []}),
            runs="[]",
            created_by=bob.id,
        )
        s.add_all([made_by_bob, unknown, batch, analysis])
        s.flush()
        ids = (made_by_bob.id, unknown.id, batch.id, analysis.id)
        s.commit()
    bobs, old, batch_id, analysis_id = ids

    by_name = {e["name"]: author_name(e) for e in client.get("/experiments").json()}
    assert by_name == {"Bob's": "Bob", "Old": None}
    assert author_name(client.get(f"/experiments/{bobs}").json()) == "Bob"
    assert author_name(client.get(f"/experiments/{old}").json()) is None
    assert [author_name(b) for b in client.get("/batches").json()] == ["Bob"]
    assert author_name(client.get(f"/batches/{batch_id}").json()) == "Bob"
    assert [author_name(a) for a in client.get("/analyses").json()] == ["Bob"]
    assert author_name(client.get(f"/analyses/{analysis_id}").json()) == "Bob"


def test_executions_name_who_launched_them(engine, client, bob):
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        s.add(dataset)
        s.flush()
        experiment = Experiment(name="Run", dataset_id=dataset.id)
        s.add(experiment)
        s.flush()
        for launcher in (bob.id, None):
            s.add(
                ExperimentExecution(
                    experiment_id=experiment.id,
                    dataset_snapshot="{}",
                    created_by=launcher,
                )
            )
        s.commit()
        experiment_id = experiment.id

    executions = client.get(f"/experiments/{experiment_id}/executions").json()

    launchers = sorted(
        (e["launched_by"] or {}).get("display_name", "") for e in executions
    )
    assert launchers == ["", "Bob"]
