import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

import async_jobs
from db import get_session
from schemas.experiments import (
    DatasetResponse,
    ExperimentAgentConfigResponse,
    ExperimentCreate,
    ExperimentResponse,
)
from tables import (
    Agent,
    Dataset,
    Experiment,
    ExperimentAgentConfig,
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

    if experiment_configs is None:
        experiment_configs = session.exec(
            select(ExperimentAgentConfig).where(
                ExperimentAgentConfig.experiment_id == experiment.id
            )
        ).all()

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
    experiment = Experiment(
        name=exp_data.name,
        description=exp_data.description,
        dataset_id=exp_data.dataset_id,
        sampling_type=exp_data.sampling_type,
        sampling_size=exp_data.sampling_size,
        sampling_start_row=exp_data.sampling_start_row,
        sampling_end_row=exp_data.sampling_end_row,
    )
    session.add(experiment)
    session.commit()
    session.refresh(experiment)

    # Create individual agent configurations for explicitly configured active agents
    default_execution_order = 1
    if exp_data.agent_teams and exp_data.agent_configurations:
        for team_id_str in exp_data.agent_teams:
            team_id = int(team_id_str)
            agents = session.exec(select(Agent).where(Agent.team_id == team_id)).all()

            for agent in agents:
                agent_config = exp_data.agent_configurations.get(str(agent.id))
                if not agent_config:
                    continue

                if not agent_config.get("is_active", True):
                    logger.info("Skipping inactive agent %s (%s)", agent.id, agent.name)
                    continue

                prompt_version_id = (
                    agent_config.get("prompt_version_id")
                    or agent.default_prompt_version_id
                )
                if not prompt_version_id:
                    logger.warning(
                        "Agent %s (%s) has no prompt version, skipping", agent.id, agent.name
                    )
                    continue

                model_id = agent_config.get("model_id") or agent.default_model_id
                if not model_id:
                    logger.warning(
                        "Agent %s (%s) has no model, skipping", agent.id, agent.name
                    )
                    continue

                # Use frontend-provided execution_order if available, otherwise auto-increment
                execution_order = agent_config.get("execution_order", default_execution_order)
                if "execution_order" not in agent_config:
                    default_execution_order += 1

                # Persist per-agent input mappings if provided
                input_mappings = agent_config.get("input_mappings")
                input_mappings_json = json.dumps(input_mappings) if input_mappings else None

                exp_agent_config = ExperimentAgentConfig(
                    experiment_id=int(experiment.id) if experiment.id is not None else 0,
                    agent_id=int(agent.id) if agent.id is not None else 0,
                    prompt_version_id=prompt_version_id,
                    model_id=model_id,
                    temperature=agent_config.get("temperature"),
                    max_tokens=agent_config.get("max_tokens"),
                    execution_order=execution_order,
                    is_active=True,
                    input_mappings=input_mappings_json,
                )
                session.add(exp_agent_config)

    session.commit()

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
