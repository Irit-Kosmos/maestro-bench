import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

import config
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
    prompts,
    providers,
    tags,
)
from api import auth as auth_api
from auth.deps import require_user
from auth.policy import validate_config
from auth.providers import setup_providers
from config import API_HOST, API_PORT, CORS_ORIGINS
from db import init_db

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
    init_db()
    logger.info("Database schema is up to date")
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
    allow_methods=["*"],
    allow_headers=["*"],
)

# Every route needs a signed-in user, except the sign-in routes and /health
PROTECTED = [Depends(require_user)]

app.include_router(auth_api.router)
app.include_router(datasets.router, dependencies=PROTECTED)
app.include_router(experiments.router, dependencies=PROTECTED)
app.include_router(agent_teams.router, dependencies=PROTECTED)
app.include_router(agents.router, dependencies=PROTECTED)
app.include_router(aggregators.router, dependencies=PROTECTED)
app.include_router(experiment_executions.router, dependencies=PROTECTED)
app.include_router(prompts.router, dependencies=PROTECTED)
app.include_router(models.router, dependencies=PROTECTED)
app.include_router(providers.router, dependencies=PROTECTED)
app.include_router(analyses.router, dependencies=PROTECTED)
app.include_router(tags.router, dependencies=PROTECTED)
app.include_router(batches.router, dependencies=PROTECTED)
app.include_router(dashboard.router, dependencies=PROTECTED)
app.include_router(events.router, dependencies=PROTECTED)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": API_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)
