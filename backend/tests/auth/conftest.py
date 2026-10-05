import pytest

import config


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
