import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlmodel import Session

import main
from db import get_session


class BrokenSession:
    def exec(self, *args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


@pytest.fixture
def client(engine):
    def _session():
        with Session(engine) as session:
            yield session

    main.app.dependency_overrides[get_session] = _session
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def test_it_is_healthy_while_the_database_answers(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_it_is_unhealthy_when_the_database_does_not_answer(client):
    main.app.dependency_overrides[get_session] = lambda: BrokenSession()

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
