from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from db import get_session
from tables import Experiment, Dataset, ExperimentExecution, AgentExecutionSnapshot
from schemas.experiment_executions import (
    ExperimentExecutionResponse,
    ExperimentExecutionUpdate,
    AgentExecutionSnapshotResponse,
    ExperimentTrace,
)
from typing import List
import json
from pathlib import Path

router = APIRouter(tags=["experiment-executions"])


@router.get(
    "/experiments/{experiment_id}/executions",
    response_model=List[ExperimentExecutionResponse],
)
def get_experiment_executions(
    experiment_id: int, session: Annotated[Session, Depends(get_session)]
):
    """Get all executions for a specific experiment"""
    executions = session.exec(
        select(ExperimentExecution).where(
            ExperimentExecution.experiment_id == experiment_id
        )
    ).all()

    result = []
    for execution in executions:
        # Get agent execution configs
        agent_configs = session.exec(
            select(AgentExecutionSnapshot).where(
                AgentExecutionSnapshot.execution_id == execution.id
            )
        ).all()

        agent_config_responses = [
            AgentExecutionSnapshotResponse(
                id=int(config.id) if config.id is not None else 0,
                agent_id=config.agent_id,
                agent_name_snapshot=config.agent_name_snapshot,
                model_name_snapshot=config.model_name_snapshot,
                model_provider_snapshot=config.model_provider_snapshot,
                prompt_name_snapshot=config.prompt_name_snapshot,
                prompt_version_snapshot=config.prompt_version_snapshot,
                final_system_prompt=config.final_system_prompt,
                final_user_prompt=config.final_user_prompt,
                final_variables=config.final_variables,
                final_temperature=config.final_temperature,
                final_max_tokens=config.final_max_tokens,
                execution_order=config.execution_order,
                created_at=config.created_at,
            )
            for config in agent_configs
        ]

        result.append(
            ExperimentExecutionResponse(
                id=int(execution.id) if execution.id is not None else 0,
                experiment_id=execution.experiment_id,
                started_at=execution.started_at,
                completed_at=execution.completed_at,
                status=execution.status,
                dataset_snapshot=execution.dataset_snapshot,
                results_file_path=execution.results_file_path,
                agent_executions=agent_config_responses,
            )
        )

    return result


@router.get("/executions/{execution_id}", response_model=ExperimentExecutionResponse)
def get_execution_details(
    execution_id: int, session: Annotated[Session, Depends(get_session)]
):
    """Get detailed information about a specific execution"""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Get agent execution snapshots
    agent_configs = session.exec(
        select(AgentExecutionSnapshot).where(
            AgentExecutionSnapshot.execution_id == execution_id
        )
    ).all()

    agent_config_responses = [
        AgentExecutionSnapshotResponse(
            id=int(config.id) if config.id is not None else 0,
            agent_id=config.agent_id,
            agent_name_snapshot=config.agent_name_snapshot,
            model_name_snapshot=config.model_name_snapshot,
            model_provider_snapshot=config.model_provider_snapshot,
            prompt_name_snapshot=config.prompt_name_snapshot,
            prompt_version_snapshot=config.prompt_version_snapshot,
            final_system_prompt=config.final_system_prompt,
            final_user_prompt=config.final_user_prompt,
            final_variables=config.final_variables,
            final_temperature=config.final_temperature,
            final_max_tokens=config.final_max_tokens,
            execution_order=config.execution_order,
            created_at=config.created_at,
        )
        for config in agent_configs
    ]

    return ExperimentExecutionResponse(
        id=int(execution.id) if execution.id is not None else 0,
        experiment_id=execution.experiment_id,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        status=execution.status,
        dataset_snapshot=execution.dataset_snapshot,
        results_file_path=execution.results_file_path,
        agent_executions=agent_config_responses,
    )


@router.get("/executions/{execution_id}/trace", response_model=ExperimentTrace)
def get_execution_trace(
    execution_id: int, session: Annotated[Session, Depends(get_session)]
):
    """Get complete scientific trace of an execution - the gold standard for reproducibility"""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Get experiment and dataset info
    experiment = session.get(Experiment, execution.experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Associated experiment not found")

    session.get(Dataset, experiment.dataset_id)

    # Get agent execution snapshots
    agent_configs = session.exec(
        select(AgentExecutionSnapshot).where(
            AgentExecutionSnapshot.execution_id == execution_id
        )
    ).all()

    agent_config_responses = [
        AgentExecutionSnapshotResponse(
            id=int(config.id) if config.id is not None else 0,
            agent_id=config.agent_id,
            agent_name_snapshot=config.agent_name_snapshot,
            model_name_snapshot=config.model_name_snapshot,
            model_provider_snapshot=config.model_provider_snapshot,
            prompt_name_snapshot=config.prompt_name_snapshot,
            prompt_version_snapshot=config.prompt_version_snapshot,
            final_system_prompt=config.final_system_prompt,
            final_user_prompt=config.final_user_prompt,
            final_variables=config.final_variables,
            final_temperature=config.final_temperature,
            final_max_tokens=config.final_max_tokens,
            execution_order=config.execution_order,
            created_at=config.created_at,
        )
        for config in agent_configs
    ]

    execution_response = ExperimentExecutionResponse(
        id=int(execution.id) if execution.id is not None else 0,
        experiment_id=execution.experiment_id,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        status=execution.status,
        dataset_snapshot=execution.dataset_snapshot,
        results_file_path=execution.results_file_path,
        agent_executions=agent_config_responses,
    )

    # Load results summary from file if available
    results_summary: dict = {}
    if execution.results_file_path and Path(execution.results_file_path).exists():
        try:
            with Path(execution.results_file_path).open("r") as f:
                results_data = json.load(f)
                results_summary = results_data.get("metadata", {})
        except Exception as e:
            print(f"Warning: Could not load results file: {e}")

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
        results_summary=results_summary,
    )


@router.put("/executions/{execution_id}", response_model=ExperimentExecutionResponse)
def update_execution(
    execution_id: int,
    update_data: ExperimentExecutionUpdate,
    session: Annotated[Session, Depends(get_session)],
):
    """Update execution details - mainly for MAESTRO to report completion"""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(execution, field, value)

    session.add(execution)
    session.commit()
    session.refresh(execution)
    # Return updated execution with agent snapshots
    agent_configs = session.exec(
        select(AgentExecutionSnapshot).where(
            AgentExecutionSnapshot.execution_id == execution_id
        )
    ).all()

    agent_config_responses = [
        AgentExecutionSnapshotResponse(
            id=int(config.id) if config.id is not None else 0,
            agent_id=config.agent_id,
            agent_name_snapshot=config.agent_name_snapshot,
            model_name_snapshot=config.model_name_snapshot,
            model_provider_snapshot=config.model_provider_snapshot,
            prompt_name_snapshot=config.prompt_name_snapshot,
            prompt_version_snapshot=config.prompt_version_snapshot,
            final_system_prompt=config.final_system_prompt,
            final_user_prompt=config.final_user_prompt,
            final_variables=config.final_variables,
            final_temperature=config.final_temperature,
            final_max_tokens=config.final_max_tokens,
            execution_order=config.execution_order,
            created_at=config.created_at,
        )
        for config in agent_configs
    ]

    return ExperimentExecutionResponse(
        id=int(execution.id) if execution.id is not None else 0,
        experiment_id=execution.experiment_id,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        status=execution.status,
        dataset_snapshot=execution.dataset_snapshot,
        results_file_path=execution.results_file_path,
        agent_executions=agent_config_responses,
    )


@router.get("/executions/{execution_id}/results", response_class=FileResponse)
def download_results(
    execution_id: int, session: Annotated[Session, Depends(get_session)]
):
    """Download the results file of an execution"""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if (
        not execution.results_file_path
        or not Path(execution.results_file_path).exists()
    ):
        raise HTTPException(status_code=404, detail="Results file not found")

    return FileResponse(
        execution.results_file_path,
        media_type="application/octet-stream",
        filename=Path(execution.results_file_path).name,
    )


@router.get("/executions/{execution_id}/download-results")
def download_execution_results(
    execution_id: int, session: Annotated[Session, Depends(get_session)]
):
    """Download the results file for a specific execution"""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if not execution.results_file_path:
        raise HTTPException(
            status_code=404, detail="No results file available for this execution"
        )

    results_file = Path(execution.results_file_path)

    # Check if file exists
    if not results_file.exists():
        raise HTTPException(status_code=404, detail="Results file not found on disk")

    # Generate a descriptive filename for download
    experiment = session.get(Experiment, execution.experiment_id)
    experiment_name = (
        experiment.name if experiment else f"experiment_{execution.experiment_id}"
    )

    # Clean experiment name for filename (remove invalid characters)
    safe_experiment_name = "".join(
        c for c in experiment_name if c.isalnum() or c in (" ", "-", "_")
    ).rstrip()
    safe_experiment_name = safe_experiment_name.replace(" ", "_")

    download_filename = f"{safe_experiment_name}_execution_{execution_id}_results.json"

    return FileResponse(
        path=str(results_file),
        filename=download_filename,
        media_type="application/json",
    )
