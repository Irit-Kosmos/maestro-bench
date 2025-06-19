"""
Request and response models for experiments API
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from schemas.agent_teams import AgentTeamResponse, ExperimentConfigResponse


class DatasetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    file_path: Optional[str]
    created_at: datetime


class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    dataset_id: int
    agent_teams: Optional[List[str]] = []  # List of team IDs as strings
    agent_configurations: Optional[dict] = {}  # Agent ID -> custom config mapping


class ExperimentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    dataset_id: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    dataset: Optional[DatasetResponse] = None
    experiment_configs: List[ExperimentConfigResponse] = []


class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    completed_at: Optional[datetime] = None


# Forward reference resolution
ExperimentResponse.model_rebuild()
