from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel
from db import engine
from api import datasets, experiments, agent_teams, agents
import uvicorn
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Support both ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router)
app.include_router(experiments.router)
app.include_router(agent_teams.router)
app.include_router(agents.router)

@app.on_event("startup")
def seed_db():
    SQLModel.metadata.create_all(engine)  # Ensure tables exist

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)