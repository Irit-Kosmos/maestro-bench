"""
Request and response models for experiments API
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from schemas.experiment_executions import LatestExecutionFigures


class DatasetResponse(BaseModel):
    id: int
    name: str
    description: str | None
    file_path: str | None
    created_at: datetime


class ExperimentAgentConfigResponse(BaseModel):
    """Response model for experiment agent configurations"""

    id: int
    experiment_id: int
    agent_id: int
    prompt_version_id: int | None
    model_id: int | None
    temperature: float | None
    max_tokens: int | None
    execution_order: int
    is_active: bool
    input_mappings: list[dict] | None = None
    created_at: datetime


class ExperimentCreate(BaseModel):
    name: str
    description: str | None = None
    dataset_id: int
    agent_teams: list[str] | None = []
    agent_configurations: dict | None = {}

    # Dataset sampling configuration
    sampling_type: str | None = None  # 'all', 'random', 'range'
    sampling_size: int | None = None
    sampling_start_row: int | None = None
    sampling_end_row: int | None = None


class ExperimentResponse(LatestExecutionFigures):
    id: int
    name: str
    description: str | None
    dataset_id: int
    status: str
    created_at: datetime
    completed_at: datetime | None
    dataset: DatasetResponse | None = None
    experiment_configs: list[ExperimentAgentConfigResponse] = []

    # Dataset sampling configuration
    sampling_type: str | None = None
    sampling_size: int | None = None
    sampling_start_row: int | None = None
    sampling_end_row: int | None = None

    # Dataset rows processed by the latest execution that has results
    row_count: int | None = None

    # Batch the experiment belongs to, and its coordinates in the batch's grid
    # ({agent_id: {field: value}})
    batch_id: int | None = None
    batch_name: str | None = None
    variant: dict[int, dict] | None = None


# Forward reference resolution
ExperimentResponse.model_rebuild()
