# MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
# Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
# Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Request and response models for analyses API
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from schemas.people import PersonResponse
from schemas.tags import TagResponse


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
    tag_ids: list[int] = []


class AnalysisUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: AnalysisConfigSchema | None = None
    runs: list[AnalysisRunRef] | None = None
    # Left out: the tags stay as they are. Sent: they become exactly these.
    tag_ids: list[int] | None = None


class AnalysisResponse(BaseModel):
    id: int
    name: str
    description: str | None
    config: AnalysisConfigSchema
    runs: list[AnalysisRunRef]
    tags: list[TagResponse] = []
    # None when nobody is known to have made it (made before authors were kept, or the account is gone)
    author: PersonResponse | None = None
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


class AgentRowOutput(BaseModel):
    name: str | None
    kind: str = "llm"
    # Aggregators: the value each formula variable resolved to
    inputs: dict[str, Any] | None = None
    # Parsed when the agent answered with JSON, the raw text otherwise
    output: Any = None
    error: str | None = None


class ExecutionRow(BaseModel):
    """One dataset row of an execution: what went in, what each agent returned."""

    row_index: int
    input_data: dict[str, Any]
    agents: list[AgentRowOutput]
    error: str | None = None


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
