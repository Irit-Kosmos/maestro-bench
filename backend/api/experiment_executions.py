import json
from collections import defaultdict

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, col, select

from db import SessionDep
from results_files import execution_row_count, results_path
from schemas.experiment_executions import (
    AgentExecutionSnapshotResponse,
    ExecutionListAgent,
    ExecutionListItem,
    ExperimentExecutionResponse,
    ExperimentTrace,
)
from tables import (
    Agent,
    AgentExecutionSnapshot,
    Batch,
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
    return [
        ExperimentExecutionResponse(
            id=int(execution.id) if execution.id is not None else 0,
            experiment_id=execution.experiment_id,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            status=execution.status,
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


@router.get("/executions", response_model=list[ExecutionListItem])
def list_executions(session: SessionDep):
    """Every execution of every experiment, newest first, whatever its status."""
    executions = session.exec(
        select(ExperimentExecution).order_by(
            col(ExperimentExecution.started_at).desc(),
            col(ExperimentExecution.id).desc(),
        )
    ).all()

    experiments = {e.id: e for e in session.exec(select(Experiment)).all()}
    batches = {b.id: b for b in session.exec(select(Batch)).all()}
    live_agents = set(session.exec(select(Agent.id)).all())
    # Only the columns the list shows: the snapshots also hold the full prompts
    agents_of: dict[int, list[ExecutionListAgent]] = defaultdict(list)
    for execution_id, agent_id, kind, name, model, provider, prompt, version in (
        session.exec(
            select(
                AgentExecutionSnapshot.execution_id,
                AgentExecutionSnapshot.agent_id,
                AgentExecutionSnapshot.kind,
                AgentExecutionSnapshot.agent_name_snapshot,
                AgentExecutionSnapshot.model_name_snapshot,
                AgentExecutionSnapshot.model_provider_snapshot,
                AgentExecutionSnapshot.prompt_name_snapshot,
                AgentExecutionSnapshot.prompt_version_snapshot,
            ).order_by(col(AgentExecutionSnapshot.execution_order))
        ).all()
    ):
        agents_of[execution_id].append(
            ExecutionListAgent(
                agent_id=agent_id if agent_id in live_agents else None,
                kind=kind,
                name=name,
                model=model,
                provider=provider,
                prompt=prompt,
                prompt_version=version,
            )
        )

    items = []
    for execution in executions:
        experiment = experiments.get(execution.experiment_id)
        batch = batches.get(experiment.batch_id) if experiment else None
        dataset_name = json.loads(execution.dataset_snapshot).get("name")
        duration = None
        if execution.completed_at:
            duration = (execution.completed_at - execution.started_at).total_seconds()
        items.append(
            ExecutionListItem(
                id=int(execution.id or 0),
                experiment_id=execution.experiment_id,
                experiment_name=experiment.name if experiment else "Unknown",
                batch_id=batch.id if batch else None,
                batch_name=batch.name if batch else None,
                dataset_name=dataset_name,
                status=execution.status,
                started_at=execution.started_at,
                completed_at=execution.completed_at,
                duration_seconds=duration,
                rows_total=execution.rows_total,
                rows_done=execution.rows_done,
                rows_failed=execution.rows_failed,
                row_count=execution_row_count(execution),
                has_results=bool(execution.results_file_path),
                total_tokens=execution.total_tokens,
                total_cost_usd=execution.total_cost_usd,
                agents=agents_of.get(int(execution.id or 0), []),
            )
        )
    return items


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
