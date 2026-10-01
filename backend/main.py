import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import (
    agent_teams,
    agents,
    analyses,
    batches,
    datasets,
    experiment_executions,
    experiments,
    models,
    prompts,
    providers,
)
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
    """Application lifespan: initialize DB on startup."""
    init_db()
    logger.info("Database tables initialized")
    logger.info("MAESTRO-bench API started")
    yield


app = FastAPI(
    title="MAESTRO-bench API",
    description="Experiment benchmarking platform for multi-agent LLM pipelines",
    version=API_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router)
app.include_router(experiments.router)
app.include_router(agent_teams.router)
app.include_router(agents.router)
app.include_router(experiment_executions.router)
app.include_router(prompts.router)
app.include_router(models.router)
app.include_router(providers.router)
app.include_router(analyses.router)
app.include_router(batches.router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": API_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)
