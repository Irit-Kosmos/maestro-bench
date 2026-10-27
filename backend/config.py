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

# Connections kept open to Postgres, and how many more a burst may open. A request holds
# one while it queries (a worker thread serves one request at a time).
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
# How long a request waits for a free connection before giving up
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
# Limits set on every connection, in milliseconds (0 turns one off): a query that runs
# too long, a wait for a lock, and a transaction left open without doing anything. They
# keep one stuck request from holding the database, and the locks, for everyone.
DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "60000"))
DB_LOCK_TIMEOUT_MS = int(os.getenv("DB_LOCK_TIMEOUT_MS", "10000"))
DB_IDLE_IN_TRANSACTION_TIMEOUT_MS = int(
    os.getenv("DB_IDLE_IN_TRANSACTION_TIMEOUT_MS", "300000")
)

# Root of everything the app stores on disk. Each workspace has its own folder,
# <DATA_DIR>/workspaces/<id>/, with its datasets in datasets/ and its execution
# results in results/. Paths kept in the database are relative to those folders.
DATA_DIR = Path(os.getenv("DATA_DIR") or Path(__file__).resolve().parent.parent)

# Largest dataset file accepted by an upload
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))

# Experiments running at the same time. The ones over the limits wait in a queue.
# One workspace cannot take all the slots of the instance.
MAX_CONCURRENT_EXPERIMENTS = int(os.getenv("MAX_CONCURRENT_EXPERIMENTS", "8"))
MAX_CONCURRENT_EXPERIMENTS_PER_WORKSPACE = int(
    os.getenv("MAX_CONCURRENT_EXPERIMENTS_PER_WORKSPACE", "3")
)

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

# Encrypts the API keys that workspaces store (at least 32 random characters).
# Without it workspaces cannot store keys and only the instance's keys are used.
# Unlike SECRET_KEY, changing it makes the stored keys unreadable.
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# Whether a workspace without its own key for a provider may use the instance's key
# (the environment variable). Off, every workspace must bring its own keys; providers
# configured by URL (Ollama) are instance-wide and unaffected.
PROVIDERS_INSTANCE_FALLBACK = (
    os.getenv("PROVIDERS_INSTANCE_FALLBACK", "true").lower() == "true"
)

# Where the browser reaches the UI and the API; the OAuth redirect URI registered
# in GitLab is <PUBLIC_API_URL>/auth/gitlab/callback.
FRONTEND_URL = os.getenv("FRONTEND_URL") or (CORS_ORIGINS[0] if CORS_ORIGINS else "")
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", f"http://localhost:{API_PORT}").rstrip("/")

# Whether editors can create public read-only links to an experiment, a batch, an
# analysis or a study. Off, the links already made stop answering too.
PUBLIC_SHARING_ENABLED = os.getenv("PUBLIC_SHARING_ENABLED", "true").lower() == "true"

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
