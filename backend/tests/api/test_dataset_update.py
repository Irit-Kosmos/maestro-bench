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

from api import datasets
from tables import Dataset
from tests.conftest import api_client, scoped


@pytest.fixture
def client(engine, data_dir):
    return api_client(engine, datasets)


@pytest.fixture
def dataset_id(engine):
    with scoped(engine) as s:
        dataset = Dataset(name="Answers", description="First batch", file_path="a.csv")
        s.add(dataset)
        s.commit()
        s.refresh(dataset)
        return dataset.id


def test_a_dataset_is_renamed_and_described(client, dataset_id, engine):
    response = client.put(
        f"/datasets/{dataset_id}", json={"name": " Questions ", "description": " Second "}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Questions"
    assert response.json()["description"] == "Second"
    with scoped(engine) as s:
        stored = s.get(Dataset, dataset_id)
        assert (stored.name, stored.description) == ("Questions", "Second")
        assert stored.file_path == "a.csv"


def test_what_is_not_sent_is_left_as_it_is(client, dataset_id):
    renamed = client.put(f"/datasets/{dataset_id}", json={"name": "Questions"}).json()
    assert renamed["description"] == "First batch"

    described = client.put(f"/datasets/{dataset_id}", json={"description": "Other"}).json()
    assert described["name"] == "Questions"


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_an_empty_description_clears_it(client, dataset_id, empty):
    response = client.put(f"/datasets/{dataset_id}", json={"description": empty})

    assert response.status_code == 200
    assert response.json()["description"] is None


@pytest.mark.parametrize("name", ["", "   "])
def test_a_dataset_keeps_a_name(client, dataset_id, engine, name):
    response = client.put(f"/datasets/{dataset_id}", json={"name": name})

    assert response.status_code == 422
    with scoped(engine) as s:
        assert s.get(Dataset, dataset_id).name == "Answers"


def test_the_file_cannot_be_swapped_through_an_update(client, dataset_id, engine):
    client.put(f"/datasets/{dataset_id}", json={"file_path": "../secret.csv"})

    with scoped(engine) as s:
        assert s.get(Dataset, dataset_id).file_path == "a.csv"


def test_an_unknown_dataset_is_not_found(client):
    assert client.put("/datasets/999", json={"name": "x"}).status_code == 404
