"""
Response models for the dashboard API
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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
    models: list[str] = []
    row_count: int | None = None
    duration_seconds: float | None = None
    total_tokens: int | None = None
    total_cost_usd: float | None = None


class DashboardActivity(BaseModel):
    """What was run over the last `days` days."""

    days: int
    experiments: int
    total_tokens: int
    total_cost_usd: float
    # Experiments in flight right now, whatever their age
    active: int


class DashboardResponse(BaseModel):
    activity: DashboardActivity
    recent_experiments: list[DashboardExperiment]
