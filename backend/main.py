import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

import async_jobs
import config
import credentials
from api import (
    agent_teams,
    agents,
    aggregators,
    analyses,
    batches,
    dashboard,
    datasets,
    events,
    experiment_executions,
    experiments,
    models,
    notes,
    prompts,
    providers,
    setup,
    studies,
    tags,
)
from api import auth as auth_api
from api import invitations as invitations_api
from api import workspaces as workspaces_api
from auth.policy import validate_config
from auth.providers import setup_providers
from auth.workspaces import scope_to_workspace
from config import API_HOST, API_PORT, CORS_ORIGINS
from db import SessionDep, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

API_VERSION = "2.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: check the auth settings and migrate the DB on startup."""
    validate_config([p.name for p in setup_providers()])
    credentials.check_config()
    init_db()
    logger.info("Database schema is up to date")
    if interrupted := async_jobs.reap_interrupted_runs():
        logger.warning("Marked %d experiment(s) left running as interrupted", interrupted)
    logger.info("MAESTRO-bench API started")
    yield


app = FastAPI(
    title="MAESTRO-bench API",
    description="Experiment benchmarking platform for multi-agent LLM pipelines",
    version=API_VERSION,
    lifespan=lifespan,
)

# Only holds the OAuth state for the few minutes of a sign-in
app.add_middleware(
    SessionMiddleware,
    secret_key=config.SECRET_KEY,
    session_cookie="maestro_oauth",
    max_age=600,
    same_site="lax",
    https_only=config.COOKIE_SECURE,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    # What the interface uses, and nothing else
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Accept", "Content-Type", "Last-Event-ID", "X-CSRF-Token"],
)

app.include_router(auth_api.router)
app.include_router(workspaces_api.router)
app.include_router(invitations_api.router)

# What a workspace holds lives under /workspaces/{slug}: the user must belong to it,
# with the role the route needs, and the request's database session only sees it
WORKSPACE_ROUTERS = [
    datasets,
    experiments,
    agent_teams,
    agents,
    aggregators,
    experiment_executions,
    prompts,
    models,
    providers,
    analyses,
    tags,
    studies,
    notes,
    batches,
    dashboard,
    events,
    setup,
]
for module in WORKSPACE_ROUTERS:
    app.include_router(
        module.router,
        prefix="/workspaces/{slug}",
        dependencies=[Depends(scope_to_workspace)],
    )


@app.get("/health")
def health_check(session: SessionDep):
    """Whether the API can serve: 200 when the database answers, 503 when it does not."""
    try:
        session.exec(text("SELECT 1"))
    except Exception:
        logger.exception("The database does not answer")
        return JSONResponse(
            {"status": "unhealthy", "version": API_VERSION}, status_code=503
        )
    return {
        "status": "healthy",
        "version": API_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)
