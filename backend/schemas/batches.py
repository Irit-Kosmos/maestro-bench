"""
Request and response models for batches API
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from schemas.experiment_executions import LatestExecutionFigures

VariableField = Literal["model_id", "prompt_version_id", "temperature"]


class VariationSpec(BaseModel):
    """One axis of a batch's grid: an agent field and the values it takes."""

    agent_id: int
    field: VariableField
    # A temperature of None is the model's own default
    values: list[int | float | None] = Field(min_length=1)


class BatchBaseConfig(BaseModel):
    """What every experiment of the batch shares (the same as an experiment's)."""

    dataset_id: int
    agent_teams: list[str] = []
    agent_configurations: dict = {}

    sampling_type: str | None = None  # 'all', 'random', 'range'
    sampling_size: int | None = None
    sampling_start_row: int | None = None
    sampling_end_row: int | None = None


class BatchCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    # Experiment the batch is derived from; not part of the batch
    base_experiment_id: int | None = None
    config: BatchBaseConfig
    # Each axis includes the value of the base configuration: it is one of the runs
    variations: list[VariationSpec] = Field(min_length=1)
    # Leave out the run where every axis has its base value, when the base is an
    # experiment that already exists (base_experiment_id)
    skip_base_point: bool = False


class VariationValueResponse(BaseModel):
    value: int | float | None
    label: str


class VariationResponse(BaseModel):
    agent_id: int
    agent_name: str
    field: VariableField
    values: list[VariationValueResponse]


class VariantCoordinate(BaseModel):
    """Where an experiment sits on one axis."""

    agent_id: int
    field: VariableField
    value: int | float | None
    label: str


class BatchExperimentResponse(LatestExecutionFigures):
    id: int
    name: str
    status: str
    coordinates: list[VariantCoordinate]
    created_at: datetime
    # Latest execution of the experiment
    execution_id: int | None = None
    execution_status: str | None = None
    # Latest execution that completed, which is not always the latest one
    last_completed_execution_id: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    row_count: int | None = None
    # Agents of the latest execution, in run order
    agent_names: list[str] = []


class BatchResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime
    base_experiment_id: int | None
    base_experiment_name: str | None = None
    dataset_id: int | None = None
    dataset_name: str | None = None
    variations: list[VariationResponse]
    # pending, running, completed, partial (not all completed), failed or cancelled
    status: str
    counts: dict[str, int]
    # Executions of all the experiments. The tokens and cost add up the latest
    # execution of each, which are the ones the experiments table shows
    execution_count: int = 0
    # Status of the executions that are not the latest of their experiment,
    # from the newest to the oldest
    earlier_execution_statuses: list[str] = []
    total_tokens: int | None = None
    total_cost_usd: float | None = None
    experiments: list[BatchExperimentResponse]


class BatchCancelResponse(BaseModel):
    batch_id: int
    cancelled: int


class BatchRerunResponse(BaseModel):
    batch_id: int
    started: int
    skipped: int
