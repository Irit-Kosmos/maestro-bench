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
