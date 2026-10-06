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


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
def test_the_interface_may_use_its_methods(client, method):
    response = preflight(client, method, "Content-Type, X-CSRF-Token")

    assert response.status_code == 200
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
