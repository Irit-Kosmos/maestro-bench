"""Moments are stored with their time zone and handled as aware UTC datetimes."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import DateTime
from sqlmodel import Session, SQLModel, select

import tables  # noqa: F401  (registers every table on SQLModel.metadata)
from api import experiments
from db import get_session
from tables import Dataset, Experiment, Workspace
from tests.conftest import TEST_WORKSPACE_ID, scoped
from workspace_scope import scope_session


def datetime_columns():
    return [
        (table.name, column)
        for table in SQLModel.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, DateTime)
    ]


@pytest.mark.parametrize(
    ("table", "column"),
    [(t, c) for t, c in datetime_columns()],
    ids=lambda value: getattr(value, "name", value),
)
def test_every_moment_column_keeps_its_time_zone(table, column):
    assert column.type.timezone, f"{table}.{column.name} is a naive timestamp"


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


def test_the_database_moments_are_aware(engine):
    with Session(engine) as s:
        workspace = s.exec(select(Workspace)).one()

    assert workspace.created_at.tzinfo is not None


def test_the_api_serializes_moments_with_an_offset(engine):
    app = FastAPI()
    app.include_router(experiments.router)

    def _session():
        with Session(engine) as session:
            scope_session(session, TEST_WORKSPACE_ID)
            yield session

    app.dependency_overrides[get_session] = _session
    with scoped(engine) as s:
        dataset = Dataset(name="d", file_path="d.csv")
        s.add(dataset)
        s.flush()
        s.add(Experiment(name="e", dataset_id=dataset.id))
        s.commit()

    created_at = TestClient(app).get("/experiments").json()[0]["created_at"]

    assert created_at.endswith(("Z", "+00:00"))
