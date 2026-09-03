import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from db import get_session
from schemas.experiment_executions import (
    AgentExecutionSnapshotResponse,
    ExperimentExecutionResponse,
    ExperimentTrace,
)
from tables import AgentExecutionSnapshot, Experiment, ExperimentExecution

router = APIRouter(tags=["experiment-executions"])


# ---------------------------------------------------------------------------
# Response builder helper
# ---------------------------------------------------------------------------


def _build_snapshot_responses(
    execution_id: int, session: Session
) -> list[AgentExecutionSnapshotResponse]:
    """Return AgentExecutionSnapshotResponse list for a given execution."""
    snapshots = session.exec(
        select(AgentExecutionSnapshot).where(
            AgentExecutionSnapshot.execution_id == execution_id
        )
    ).all()
    return [
        AgentExecutionSnapshotResponse(
            id=int(s.id) if s.id is not None else 0,
            agent_id=s.agent_id,
            agent_name_snapshot=s.agent_name_snapshot,
            agent_team_name_snapshot=(
                s.agent.team.name if s.agent and s.agent.team else None
            ),
            model_name_snapshot=s.model_name_snapshot,
            model_provider_snapshot=s.model_provider_snapshot,
            prompt_name_snapshot=s.prompt_name_snapshot,
            prompt_version_snapshot=s.prompt_version_snapshot,
            final_system_prompt=s.final_system_prompt,
            final_user_prompt=s.final_user_prompt,
            final_variables=s.final_variables,
            final_input_mappings=s.final_input_mappings,
            final_temperature=s.final_temperature,
            final_max_tokens=s.final_max_tokens,
            execution_order=s.execution_order,
            created_at=s.created_at,
        )
        for s in snapshots
    ]


def _build_execution_response(
    execution: ExperimentExecution, session: Session
) -> ExperimentExecutionResponse:
    return ExperimentExecutionResponse(
        id=int(execution.id) if execution.id is not None else 0,
        experiment_id=execution.experiment_id,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        status=execution.status,
        dataset_snapshot=execution.dataset_snapshot,
        results_file_path=execution.results_file_path,
        agent_executions=_build_snapshot_responses(execution.id, session),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/experiments/{experiment_id}/executions",
    response_model=list[ExperimentExecutionResponse],
)
def get_experiment_executions(
    experiment_id: int, session: Annotated[Session, Depends(get_session)]
):
    """Get all executions for a specific experiment."""
    executions = session.exec(
        select(ExperimentExecution).where(
            ExperimentExecution.experiment_id == experiment_id
        )
    ).all()
    return [_build_execution_response(exc, session) for exc in executions]


@router.get("/executions/{execution_id}", response_model=ExperimentExecutionResponse)
def get_execution_details(
    execution_id: int, session: Annotated[Session, Depends(get_session)]
):
    """Get detailed information about a specific execution."""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return _build_execution_response(execution, session)


@router.get("/executions/{execution_id}/trace", response_model=ExperimentTrace)
def get_execution_trace(
    execution_id: int, session: Annotated[Session, Depends(get_session)]
):
    """Get the complete scientific trace of an execution."""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    experiment = session.get(Experiment, execution.experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Associated experiment not found")

    execution_response = _build_execution_response(execution, session)
    agent_config_responses = _build_snapshot_responses(execution_id, session)

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
    execution_id: int, session: Annotated[Session, Depends(get_session)]
):
    """Download the results file for a specific execution."""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if not execution.results_file_path:
        raise HTTPException(
            status_code=404, detail="No results file available for this execution"
        )

    results_file = Path(execution.results_file_path)
    if not results_file.exists():
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
