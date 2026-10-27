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

"""Moments are stored with their time zone and handled as aware UTC datetimes."""

from datetime import UTC, datetime, timedelta, timezone

from sqlalchemy import DateTime
from sqlmodel import SQLModel, select

import tables  # noqa: F401  (registers every table on SQLModel.metadata)
from api import experiments
from tables import Dataset, Experiment
from tests.conftest import api_client, scoped


def test_every_moment_column_keeps_its_time_zone():
    naive = [
        f"{table.name}.{column.name}"
        for table in SQLModel.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, DateTime) and not column.type.timezone
    ]

    assert naive == []


def test_a_moment_keeps_its_instant_whatever_its_offset(engine):
    paris = timezone(timedelta(hours=2))
    written = datetime(2026, 3, 1, 12, 0, tzinfo=paris)
    with scoped(engine) as s:
        s.add(Dataset(name="d", file_path="d.csv", created_at=written))
        s.commit()

    with scoped(engine) as s:
        read = s.exec(select(Dataset)).one().created_at

    assert read == written
    assert read.utcoffset() == timedelta(0)
    assert read.hour == 10


def test_a_naive_datetime_is_read_as_utc(engine):
    with scoped(engine) as s:
        naive = datetime(2026, 3, 1, 12)  # noqa: DTZ001
        s.add(Dataset(name="d", file_path="d.csv", created_at=naive))
        s.commit()

    with scoped(engine) as s:
        read = s.exec(select(Dataset)).one().created_at

    assert read == datetime(2026, 3, 1, 12, tzinfo=UTC)


def test_the_api_serializes_moments_with_an_offset(engine):
    client = api_client(engine, experiments)
    with scoped(engine) as s:
        dataset = Dataset(name="d", file_path="d.csv")
        s.add(dataset)
        s.flush()
        s.add(Experiment(name="e", dataset_id=dataset.id))
        s.commit()

    created_at = client.get("/experiments").json()[0]["created_at"]

    assert created_at.endswith(("Z", "+00:00"))
