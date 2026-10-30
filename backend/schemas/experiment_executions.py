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
Request and response models for experiment executions API
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from schemas.people import PersonResponse


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
    agent_id: int | None  # empty once the agent is deleted
    # Step of the experiment it ran ("12", "12#2"…); None only on an old snapshot
    # of an agent since deleted
    step_key: str | None = None
    # "aggregator" snapshots have empty model and prompt fields, and formulas
    kind: str = "llm"
    agent_name_snapshot: str
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


class ExperimentExecutionResponse(BaseModel):
    id: int
    experiment_id: int
    started_at: datetime
    completed_at: datetime | None
    status: str
    # None when nobody is known to have launched it (launched before this was kept,
    # or the account is gone)
    launched_by: PersonResponse | None = None
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
