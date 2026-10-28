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

import json
from collections import defaultdict

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, col, select

from db import SessionDep
from loading import people
from results_files import execution_row_count, results_path
from schemas.experiment_executions import (
    AgentExecutionSnapshotResponse,
    ExperimentExecutionResponse,
    ExperimentTrace,
)
from tables import (
    AgentExecutionSnapshot,
    Experiment,
    ExperimentExecution,
)

router = APIRouter(tags=["experiment-executions"])


# ---------------------------------------------------------------------------
# Response builder helper
# ---------------------------------------------------------------------------


def _snapshot_responses(
    execution_ids: list[int], session: Session
) -> dict[int, list[AgentExecutionSnapshotResponse]]:
    """The agent snapshots of each of these executions, in one query."""
    responses: dict[int, list[AgentExecutionSnapshotResponse]] = defaultdict(list)
    if not execution_ids:
        return responses
    rows = session.exec(
        select(AgentExecutionSnapshot)
        .where(col(AgentExecutionSnapshot.execution_id).in_(execution_ids))
        .order_by(col(AgentExecutionSnapshot.id))
    ).all()
    for s in rows:
        responses[s.execution_id].append(
            AgentExecutionSnapshotResponse(
                id=int(s.id) if s.id is not None else 0,
                agent_id=s.agent_id,
                step_key=s.step_key
                or (None if s.agent_id is None else str(s.agent_id)),
                kind=s.kind,
                agent_name_snapshot=s.agent_name_snapshot,
                model_name_snapshot=s.model_name_snapshot,
                model_provider_snapshot=s.model_provider_snapshot,
                prompt_name_snapshot=s.prompt_name_snapshot,
                prompt_version_snapshot=s.prompt_version_snapshot,
                prompt_id=s.prompt_id,
                prompt_version_id=s.prompt_version_id,
                final_system_prompt=s.final_system_prompt,
                final_user_prompt=s.final_user_prompt,
                final_variables=s.final_variables,
                final_input_mappings=s.final_input_mappings,
                final_formulas=s.final_formulas,
                final_temperature=s.final_temperature,
                final_max_tokens=s.final_max_tokens,
                execution_order=s.execution_order,
                created_at=s.created_at,
            )
        )
    return responses


def _build_execution_responses(
    executions: list[ExperimentExecution], session: Session
) -> list[ExperimentExecutionResponse]:
    snapshots = _snapshot_responses([int(e.id) for e in executions], session)
    launchers = people(session, (e.created_by for e in executions))
    return [
        ExperimentExecutionResponse(
            id=int(execution.id) if execution.id is not None else 0,
            experiment_id=execution.experiment_id,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            status=execution.status,
            launched_by=launchers.get(execution.created_by),
            dataset_snapshot=execution.dataset_snapshot,
            results_file_path=execution.results_file_path,
            row_count=execution_row_count(execution),
            agent_executions=snapshots[int(execution.id)],
        )
        for execution in executions
    ]


def _build_execution_response(
    execution: ExperimentExecution, session: Session
) -> ExperimentExecutionResponse:
    return _build_execution_responses([execution], session)[0]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/experiments/{experiment_id}/executions",
    response_model=list[ExperimentExecutionResponse],
)
def get_experiment_executions(
    experiment_id: int, session: SessionDep
):
    """Get all executions for a specific experiment."""
    executions = session.exec(
        select(ExperimentExecution).where(
            ExperimentExecution.experiment_id == experiment_id
        )
    ).all()
    return _build_execution_responses(list(executions), session)


@router.get("/executions/{execution_id}", response_model=ExperimentExecutionResponse)
def get_execution_details(
    execution_id: int, session: SessionDep
):
    """Get detailed information about a specific execution."""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return _build_execution_response(execution, session)


@router.get("/executions/{execution_id}/trace", response_model=ExperimentTrace)
def get_execution_trace(
    execution_id: int, session: SessionDep
):
    """Get the complete scientific trace of an execution."""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    experiment = session.get(Experiment, execution.experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Associated experiment not found")

    execution_response = _build_execution_response(execution, session)
    agent_config_responses = execution_response.agent_executions

    return ExperimentTrace(
        execution=execution_response,
        agent_configs=agent_config_responses,
        experiment_metadata={
            "id": int(experiment.id) if experiment.id is not None else 0,
            "name": experiment.name,
            "description": experiment.description,
            "created_at": experiment.created_at.isoformat(),
            "dataset_id": experiment.dataset_id,
        },
        dataset_metadata=json.loads(execution.dataset_snapshot),
    )


@router.get("/executions/{execution_id}/results")
def download_results(
    execution_id: int, session: SessionDep
):
    """Download the results file for a specific execution."""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if not execution.results_file_path:
        raise HTTPException(
            status_code=404, detail="No results file available for this execution"
        )

    results_file = results_path(execution)
    if results_file is None or not results_file.exists():
        raise HTTPException(status_code=404, detail="Results file not found on disk")

    experiment = session.get(Experiment, execution.experiment_id)
    experiment_name = (
        experiment.name if experiment else f"experiment_{execution.experiment_id}"
    )
    safe_name = (
        "".join(c for c in experiment_name if c.isalnum() or c in (" ", "-", "_"))
        .rstrip()
        .replace(" ", "_")
    )
    filename = f"{safe_name}_execution_{execution_id}_results.json"

    return FileResponse(
        path=str(results_file),
        filename=filename,
        media_type="application/json",
    )
