"""
Request and response models for experiment executions API
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class AgentExecutionSnapshotResponse(BaseModel):
    id: int
    agent_id: int
    agent_name_snapshot: str
    model_name_snapshot: str
    model_provider_snapshot: str
    prompt_name_snapshot: str
    prompt_version_snapshot: str
    final_system_prompt: Optional[str]
    final_user_prompt: Optional[str]
    final_variables: Optional[str]
    final_temperature: Optional[float]
    final_max_tokens: Optional[int]
    execution_order: int
    created_at: datetime


class ExperimentExecutionResponse(BaseModel):
    id: int
    experiment_id: int
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    dataset_snapshot: str
    results_file_path: Optional[str]
    agent_executions: List[AgentExecutionSnapshotResponse] = []


class ExperimentExecutionUpdate(BaseModel):
    status: Optional[str] = None
    completed_at: Optional[datetime] = None
    results_file_path: Optional[str] = None


class ExperimentTrace(BaseModel):
    """Complete trace of an experiment execution — the core scientific artifact."""

    execution: ExperimentExecutionResponse
    agent_configs: List[AgentExecutionSnapshotResponse]
    experiment_metadata: dict
    dataset_metadata: dict
    results_summary: dict


# Forward reference resolution
ExperimentExecutionResponse.model_rebuild()
