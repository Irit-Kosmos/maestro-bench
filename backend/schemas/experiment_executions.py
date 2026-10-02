"""
Request and response models for experiment executions API
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LatestExecutionFigures(BaseModel):
    """An experiment's executions, as its lists show them.

    The figures are those of the latest execution; the other executions are
    only counted.
    """

    execution_count: int = 0
    duration_seconds: float | None = None
    # Dataset rows that failed, counted in the rows processed
    rows_failed: int | None = None
    total_tokens: int | None = None
    total_cost_usd: float | None = None


class AgentExecutionSnapshotResponse(BaseModel):
    id: int
    agent_id: int
    agent_name_snapshot: str
    agent_team_name_snapshot: str | None
    model_name_snapshot: str
    model_provider_snapshot: str
    prompt_name_snapshot: str
    prompt_version_snapshot: str
    prompt_id: int | None = None
    prompt_version_id: int | None = None
    final_system_prompt: str | None
    final_user_prompt: str | None
    final_variables: str | None
    final_input_mappings: str | None
    final_temperature: float | None
    final_max_tokens: int | None
    execution_order: int
    created_at: datetime


class ExperimentExecutionResponse(BaseModel):
    id: int
    experiment_id: int
    started_at: datetime
    completed_at: datetime | None
    status: str
    dataset_snapshot: str
    results_file_path: str | None
    # Dataset rows processed; None until the results file exists
    row_count: int | None = None
    agent_executions: list[AgentExecutionSnapshotResponse] = []


class ExperimentTrace(BaseModel):
    """Complete trace of an experiment execution — the core scientific artifact."""

    execution: ExperimentExecutionResponse
    agent_configs: list[AgentExecutionSnapshotResponse]
    experiment_metadata: dict
    dataset_metadata: dict


# Forward reference resolution
ExperimentExecutionResponse.model_rebuild()
