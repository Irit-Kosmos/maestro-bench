import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select

import async_jobs
from batch_utils import parse_point
from db import get_session
from experiment_utils import add_experiment
from results_files import execution_row_count
from schemas.experiments import (
    DatasetResponse,
    ExperimentAgentConfigResponse,
    ExperimentCreate,
    ExperimentResponse,
)
from tables import (
    Batch,
    Dataset,
    Experiment,
    ExperimentAgentConfig,
    ExperimentExecution,
)

router = APIRouter(tags=["experiments"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response builder helper
# ---------------------------------------------------------------------------


def _build_experiment_response(
    experiment: Experiment,
    session: Session,
    experiment_configs: list[ExperimentAgentConfig] | None = None,
) -> ExperimentResponse:
    """Build a fully-populated ExperimentResponse from an ORM Experiment."""
    dataset = session.get(Dataset, experiment.dataset_id) if experiment.dataset_id else None

    batch = session.get(Batch, experiment.batch_id) if experiment.batch_id else None

    if experiment_configs is None:
        experiment_configs = session.exec(
            select(ExperimentAgentConfig).where(
                ExperimentAgentConfig.experiment_id == experiment.id
            )
        ).all()

    latest_with_results = session.exec(
        select(ExperimentExecution)
        .where(
            ExperimentExecution.experiment_id == experiment.id,
            col(ExperimentExecution.results_file_path).is_not(None),
        )
        .order_by(col(ExperimentExecution.started_at).desc())
    ).first()

    return ExperimentResponse(
        id=int(experiment.id) if experiment.id is not None else 0,
        name=experiment.name,
        description=experiment.description,
        dataset_id=experiment.dataset_id,
        status=experiment.status,
        created_at=experiment.created_at,
        completed_at=experiment.completed_at,
        sampling_type=experiment.sampling_type,
        sampling_size=experiment.sampling_size,
        sampling_start_row=experiment.sampling_start_row,
        sampling_end_row=experiment.sampling_end_row,
        batch_id=experiment.batch_id,
        batch_name=batch.name if batch else None,
        variant=parse_point(experiment.variant) or None,
        row_count=execution_row_count(latest_with_results)
        if latest_with_results
        else None,
        dataset=DatasetResponse(
            id=int(dataset.id) if dataset.id is not None else 0,
            name=dataset.name,
            description=dataset.description,
            file_path=dataset.file_path,
            created_at=dataset.created_at,
        )
        if dataset
        else None,
        experiment_configs=[
            ExperimentAgentConfigResponse(
                id=int(config.id) if config.id is not None else 0,
                experiment_id=config.experiment_id,
                agent_id=config.agent_id,
                prompt_version_id=config.prompt_version_id,
                model_id=config.model_id,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                execution_order=config.execution_order,
                is_active=config.is_active,
                input_mappings=json.loads(config.input_mappings)
                if config.input_mappings
                else None,
                created_at=config.created_at,
            )
            for config in experiment_configs
        ],
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/experiments", response_model=list[ExperimentResponse])
def list_experiments(session: Annotated[Session, Depends(get_session)]):
    """Get all experiments"""
    experiments = session.exec(
        select(Experiment).order_by(Experiment.created_at.desc())
    ).all()
    return [_build_experiment_response(exp, session) for exp in experiments]


@router.post("/experiments", response_model=ExperimentResponse, status_code=201)
async def create_experiment(
    exp_data: ExperimentCreate, session: Annotated[Session, Depends(get_session)]
):
    """Create a new experiment and automatically start it."""
    experiment = add_experiment(session, exp_data)
    session.commit()
    session.refresh(experiment)

    experiment_id = int(experiment.id) if experiment.id is not None else 0
    try:
        async_jobs.start_experiment(experiment_id)
        logger.info("Experiment %s dispatched", experiment_id)
    except Exception:
        logger.exception("Failed to start experiment %s", experiment_id)

    return _build_experiment_response(experiment, session)


@router.get("/experiments/{exp_id}", response_model=ExperimentResponse)
def get_experiment(exp_id: int, session: Annotated[Session, Depends(get_session)]):
    """Get a specific experiment with all its configurations."""
    experiment = session.get(Experiment, exp_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return _build_experiment_response(experiment, session)


@router.delete("/experiments/{exp_id}")
def delete_experiment(exp_id: int, session: Annotated[Session, Depends(get_session)]):
    """Delete an experiment and all its data (handled by ORM cascade)."""
    experiment = session.get(Experiment, exp_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    # Batches derived from this experiment keep existing, without their origin
    for batch in session.exec(
        select(Batch).where(Batch.base_experiment_id == exp_id)
    ).all():
        batch.base_experiment_id = None
        session.add(batch)

    session.delete(experiment)
    session.commit()
    return {"message": "Experiment deleted successfully"}


@router.post("/experiments/{experiment_id}/cancel")
def cancel_experiment(experiment_id: int):
    """Cancel a running experiment task."""
    return {
        "experiment_id": experiment_id,
        "cancelled": async_jobs.cancel_experiment(experiment_id),
    }


@router.post("/experiments/{experiment_id}/rerun")
async def rerun_experiment(
    experiment_id: int, session: Annotated[Session, Depends(get_session)]
):
    """Re-run an experiment with the same configuration."""
    experiment = session.get(Experiment, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    agent_configs = session.exec(
        select(ExperimentAgentConfig).where(
            ExperimentAgentConfig.experiment_id == experiment_id
        )
    ).all()

    if not agent_configs:
        raise HTTPException(
            status_code=400, detail="Experiment has no agent configurations"
        )

    try:
        async_jobs.start_experiment(experiment_id)
        return {
            "experiment_id": experiment_id,
            "message": "Experiment re-run started successfully",
            "status": "started",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start experiment re-run: {e}"
        ) from e
