from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel
from db import engine
from api import (
    datasets,
    experiments,
    agent_teams,
    agents,
    experiment_executions,
    prompts,
    models,
)
from config import API_HOST, API_PORT
import uvicorn

app = FastAPI(
    title="MAESTRO Experiment Bench API",
    description="Complete experiment traceability system for scientific research",
    version="2.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(datasets.router)
app.include_router(experiments.router)
app.include_router(agent_teams.router)
app.include_router(agents.router)
app.include_router(experiment_executions.router)
app.include_router(prompts.router)
app.include_router(models.router)


@app.on_event("startup")
def init_db():
    """Initialize database tables"""
    SQLModel.metadata.create_all(engine)  # Ensure all tables exist
    print("🚀 MAESTRO Experiment Bench API started")
    print("📊 Database tables initialized")
    print("🔬 Full experiment traceability enabled")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)
