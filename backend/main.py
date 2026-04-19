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
    providers,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB on startup."""
    init_db()
    print("Database tables initialized")

    print("MAESTRO-bench V2 API started (standalone mode)")
    yield


app = FastAPI(
    title="MAESTRO-bench API",
    description="Standalone experiment benchmarking platform with direct LLM provider access",
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

# Existing routers
app.include_router(datasets.router)
app.include_router(experiments.router)
app.include_router(agent_teams.router)
app.include_router(agents.router)
app.include_router(experiment_executions.router)
app.include_router(prompts.router)
app.include_router(models.router)

# V2 routers
app.include_router(providers.router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "mode": "standalone",
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)
