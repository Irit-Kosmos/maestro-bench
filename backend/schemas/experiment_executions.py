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
    # Status of each execution, from the newest to the oldest
    execution_statuses: list[str] = []
    duration_seconds: float | None = None
    # Dataset rows that failed, counted in the rows processed
    rows_failed: int | None = None
    total_tokens: int | None = None
    total_cost_usd: float | None = None


class AgentExecutionSnapshotResponse(BaseModel):
    id: int
    agent_id: int
    # "aggregator" snapshots have empty model and prompt fields, and formulas
    kind: str = "llm"
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
    final_formulas: str | None = None
    final_temperature: float | None
    final_max_tokens: int | None
    execution_order: int
    created_at: datetime


class ExecutionListAgent(BaseModel):
    """One agent of an execution, as the executions list shows it."""

    # None once the agent has been deleted: only its snapshot is left
    agent_id: int | None = None
    kind: str = "llm"
    name: str
    model: str
    provider: str
    prompt: str
    prompt_version: str


class ExecutionListItem(BaseModel):
    """One execution, with the experiment it belongs to, for lists spanning experiments."""

    id: int
    experiment_id: int
    experiment_name: str
    batch_id: int | None = None
    batch_name: str | None = None
    dataset_name: str | None = None
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    # Live progress, in dataset rows; failed rows are counted in the rows done
    rows_total: int | None = None
    rows_done: int = 0
    rows_failed: int = 0
    # Dataset rows processed; None until the results file exists
    row_count: int | None = None
    has_results: bool = False
    total_tokens: int | None = None
    total_cost_usd: float | None = None
    # In the order they ran
    agents: list[ExecutionListAgent] = []


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
