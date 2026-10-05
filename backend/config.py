import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://maestro:maestro@localhost:5432/maestro"
)
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

# Root of everything the app stores on disk: datasets live in <DATA_DIR>/datasets
# and execution results in <DATA_DIR>/results. Paths kept in the database are
# relative to the directory of their kind (datasets) or to DATA_DIR (results).
DATA_DIR = Path(os.getenv("DATA_DIR") or Path(__file__).resolve().parent.parent)

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def _csv(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


# Signs the OAuth state cookie and derives the CSRF tokens. Required.
SECRET_KEY = os.getenv("SECRET_KEY", "")

# Where the browser reaches the UI and the API; the OAuth redirect URI registered
# in GitLab is <PUBLIC_API_URL>/auth/gitlab/callback.
FRONTEND_URL = os.getenv("FRONTEND_URL") or (CORS_ORIGINS[0] if CORS_ORIGINS else "")
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", f"http://localhost:{API_PORT}").rstrip("/")

SESSION_COOKIE_NAME = "maestro_session"
SESSION_IDLE_DAYS = int(os.getenv("SESSION_IDLE_DAYS", "7"))
SESSION_MAX_DAYS = int(os.getenv("SESSION_MAX_DAYS", "30"))
# The cookie is Secure whenever the UI is served over https
COOKIE_SECURE = FRONTEND_URL.startswith("https://")

# Who may sign in. Every restriction that is set must be satisfied.
AUTH_ALLOWED_EMAIL_DOMAINS = [
    domain.lstrip("@").lower() for domain in _csv("AUTH_ALLOWED_EMAIL_DOMAINS")
]
AUTH_GITLAB_ALLOWED_GROUPS = [
    group.strip("/").lower() for group in _csv("AUTH_GITLAB_ALLOWED_GROUPS")
]
# Explicit opt-in to let any account of the identity provider in
AUTH_ALLOW_ANY_USER = os.getenv("AUTH_ALLOW_ANY_USER", "false").lower() == "true"
INSTANCE_ADMINS = [email.lower() for email in _csv("INSTANCE_ADMINS")]

AUTH_GITLAB_BASE_URL = os.getenv("AUTH_GITLAB_BASE_URL", "").rstrip("/")
AUTH_GITLAB_CLIENT_ID = os.getenv("AUTH_GITLAB_CLIENT_ID", "")
AUTH_GITLAB_CLIENT_SECRET = os.getenv("AUTH_GITLAB_CLIENT_SECRET", "")

# Who may create workspaces: "any" signed-in user, or only the "admins"
WORKSPACE_CREATION = os.getenv("WORKSPACE_CREATION", "any").lower()
