from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import API_HOST, API_PORT, CORS_ORIGINS
from db import init_db
from api import (
    datasets,
    experiments,
    agent_teams,
    agents,
    experiment_executions,
    prompts,
    models,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB on startup."""
    init_db()
    print("MAESTRO Experiment Bench API started")
    print("Database tables initialized")
    yield


app = FastAPI(
    title="MAESTRO Experiment Bench API",
    description="Complete experiment traceability system for scientific research",
    version="2.0.0",
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


@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)
