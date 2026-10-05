"""
Response models for the dashboard API
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DashboardModel(BaseModel):
    name: str
    # Whose logo to show next to it
    provider: str


class DashboardExperiment(BaseModel):
    """One recent experiment, with what its latest execution produced."""

    id: int
    name: str
    status: str
    created_at: datetime
    batch_id: int | None = None
    batch_name: str | None = None
    dataset_name: str | None = None
    # Distinct models of the pipeline, in execution order
    models: list[DashboardModel] = []
    row_count: int | None = None
    duration_seconds: float | None = None
    total_tokens: int | None = None
    total_cost_usd: float | None = None


class DashboardTotals(BaseModel):
    """What was run over a stretch of time."""

    experiments: int = 0
    # Of those experiments, by how they ended
    completed: int = 0
    failed: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    # Rows the executions went through, the failed ones included
    rows_done: int = 0
    rows_failed: int = 0
    # Executions that failed, or went on with failed rows; the cancelled ones are a choice, not a problem
    executions_with_failures: int = 0


class DashboardBucket(DashboardTotals):
    """The totals of one slice of the period, `start` being its first instant."""

    start: datetime


class DashboardActiveExperiment(BaseModel):
    id: int
    name: str
    status: str


class DashboardActivity(BaseModel):
    """What was run over the period, set against the period before it."""

    range: str
    # First instant of the period; None for "all"
    since: datetime | None = None
    current: DashboardTotals
    # Same length, right before `since`. For "all", which has no before: everything older than
    # 30 days, so the change says how much it grew over that time. None when it is not older.
    previous: DashboardTotals | None = None
    # The period cut in even slices, oldest first
    buckets: list[DashboardBucket]
    # Experiments in flight right now, whatever their age
    active: list[DashboardActiveExperiment]


class DashboardResponse(BaseModel):
    activity: DashboardActivity
    recent_experiments: list[DashboardExperiment]
