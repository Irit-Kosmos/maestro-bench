"""
Request and response models for experiments API
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from schemas.experiment_executions import LatestExecutionFigures

SamplingType = Literal["all", "random", "range"]

# pandas takes seeds from 0 to 2**32 - 1
MAX_SAMPLING_SEED = 2**32 - 1


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
    # An agent may run several times in an experiment: each run is a step, told
    # apart by its key ("12", then "12#2"…). The label is None when it is the
    # agent's own name.
    step_key: str
    label: str | None = None
    prompt_version_id: int | None
    model_id: int | None
    temperature: float | None
    max_tokens: int | None
    execution_order: int
    is_active: bool
    input_mappings: list[dict] | None = None
    # Aggregators: [{name, formula}]
    formulas: list[dict] | None = None
    created_at: datetime


class ExperimentCreate(BaseModel):
    name: str
    description: str | None = None
    dataset_id: int
    # Settings of each step of the pipeline, by step key ("12", "12#2"…)
    agent_configurations: dict | None = {}

    # Dataset sampling configuration
    sampling_type: SamplingType | None = None
    sampling_size: int | None = None
    sampling_start_row: int | None = None
    sampling_end_row: int | None = None
    # Seed of a random sample: the same seed takes the same rows from the same dataset
    # and sample size. Drawn at random when left out.
    sampling_seed: int | None = Field(default=None, ge=0, le=MAX_SAMPLING_SEED)


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
    # Seed of the random sample: runs with the same seed take the same rows
    sampling_seed: int | None = None

    # Dataset rows processed by the latest execution that has results
    row_count: int | None = None
    # When the latest execution started; None while nothing has run
    last_run_at: datetime | None = None
    # The latest execution an analysis can read: completed, with its results
    latest_analyzable_execution_id: int | None = None

    # Batch the experiment belongs to, and its coordinates in the batch's grid
    # ({step_key: {field: value}})
    batch_id: int | None = None
    batch_name: str | None = None
    variant: dict[str, dict] | None = None


# Forward reference resolution
ExperimentResponse.model_rebuild()


class ExperimentCancelResponse(BaseModel):
    experiment_id: int
    # False when nothing was running or waiting for this experiment
    cancelled: bool


class ExperimentRerunResponse(BaseModel):
    experiment_id: int
    message: str
    status: Literal["started", "queued"]
