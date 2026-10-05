import pytest
from sqlmodel import Session

import config
import main
from auth.deps import get_engine
from db import get_session
from tests.auth.people import Person


@pytest.fixture(autouse=True)
def auth_config(monkeypatch):
    """A known set of authentication settings, whatever the environment says."""
    settings = {
        "SECRET_KEY": "k" * 48,
        "FRONTEND_URL": "http://localhost:3000",
        "CORS_ORIGINS": ["http://localhost:3000"],
        "PUBLIC_API_URL": "http://localhost:8000",
        "COOKIE_SECURE": False,
        "SESSION_IDLE_DAYS": 7,
        "SESSION_MAX_DAYS": 30,
        "AUTH_ALLOWED_EMAIL_DOMAINS": ["irit.fr"],
        "AUTH_GITLAB_ALLOWED_GROUPS": [],
        "AUTH_ALLOW_ANY_USER": False,
        "INSTANCE_ADMINS": [],
    }
    for name, value in settings.items():
        monkeypatch.setattr(config, name, value)


@pytest.fixture
def app(engine):
    def _session():
        with Session(engine) as session:
            yield session

    main.app.dependency_overrides[get_session] = _session
    main.app.dependency_overrides[get_engine] = lambda: engine
    yield main.app
    main.app.dependency_overrides.clear()


@pytest.fixture
def alice(engine, app):
    return Person(engine, "alice")


@pytest.fixture
def bob(engine, app):
    return Person(engine, "bob")
