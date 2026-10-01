"""
Request and response models for analyses API
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalysisConfigSchema(BaseModel):
    truth_column: str
    output_path: str = Field(
        default="", description="Dotted path in the agent output; empty = whole"
    )
    value_type: Literal["numeric", "categorical"]
    metrics: list[str]
    ignore_case: bool = False
    n_boot: int = Field(default=1000, ge=0, le=10000)
    confidence: float = Field(default=0.95, gt=0, lt=1)
    seed: int = 0


class AnalysisRunRef(BaseModel):
    execution_id: int
    agent_name: str
    label: str | None = None


class AnalysisCreate(BaseModel):
    name: str
    description: str | None = None
    config: AnalysisConfigSchema
    runs: list[AnalysisRunRef] = []


class AnalysisUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: AnalysisConfigSchema | None = None
    runs: list[AnalysisRunRef] | None = None


class AnalysisResponse(BaseModel):
    id: int
    name: str
    description: str | None
    config: AnalysisConfigSchema
    runs: list[AnalysisRunRef]
    created_at: datetime
    updated_at: datetime


class AnalysisComputeRequest(BaseModel):
    config: AnalysisConfigSchema
    runs: list[AnalysisRunRef]


class MetricInfo(BaseModel):
    key: str
    label: str
    kind: Literal["numeric", "categorical"]
    description: str
    lower_is_better: bool


class MetricValueResponse(BaseModel):
    value: float | None
    ci_low: float | None
    ci_high: float | None
    undefined_reason: str | None


class ExcludedRowResponse(BaseModel):
    row_index: int | None
    dataset_row_id: int | None
    reason: str


class RunResultResponse(BaseModel):
    execution_id: int
    agent_name: str
    label: str
    # "ok", or why the run could not be computed
    status: Literal["ok", "missing", "unavailable"]
    error: str | None = None
    experiment_id: int | None = None
    experiment_name: str | None = None
    n_valid: int = 0
    n_total: int = 0
    coverage: float | None = None
    metrics: dict[str, MetricValueResponse] = {}
    exclusions: dict[str, int] = {}
    excluded_rows: list[ExcludedRowResponse] = []
    warnings: list[str] = []
    points: list[dict[str, Any]] | None = None
    confusion: dict[str, Any] | None = None


class AnalysisResultResponse(BaseModel):
    metrics: list[MetricInfo]
    runs: list[RunResultResponse]
    warnings: list[str]


class AgentFields(BaseModel):
    name: str
    model: str | None
    execution_order: int
    # Dotted paths to scalar values found in the agent's outputs
    paths: list[str]


class ExecutionFields(BaseModel):
    execution_id: int
    columns: list[str]
    agents: list[AgentFields]


class AvailableExecution(BaseModel):
    execution_id: int
    experiment_id: int
    experiment_name: str
    dataset_name: str | None
    started_at: datetime
    completed_at: datetime | None
    # Dataset rows the execution processed
    row_count: int | None = None
    agents: list[dict[str, Any]]
