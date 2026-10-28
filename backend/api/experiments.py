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
import logging
import secrets

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, col, select

import async_jobs
from batch_utils import parse_point
from db import SessionDep
from execution_stats import latest_figures
from experiment_utils import ExperimentConfigError, add_experiment
from loading import by_id, grouped_by, people
from results_files import execution_row_count
from schemas.experiments import (
    DatasetResponse,
    ExperimentAgentConfigResponse,
    ExperimentCancelResponse,
    ExperimentCreate,
    ExperimentRerunResponse,
    ExperimentResponse,
)
from schemas.people import PersonResponse
from study_utils import clear_item_links
from tables import (
    Batch,
    Dataset,
    Experiment,
    ExperimentAgentConfig,
    ExperimentExecution,
)
from workspace_scope import current_user_id, current_workspace_id

router = APIRouter(tags=["experiments"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response builder helper
# ---------------------------------------------------------------------------


def _build_experiment_responses(
    experiments: list[Experiment], session: Session
) -> list[ExperimentResponse]:
    """Fully-populated ExperimentResponses, with a fixed number of queries."""
    ids = [e.id for e in experiments if e.id is not None]
    datasets = by_id(session, Dataset, (e.dataset_id for e in experiments))
    batches = by_id(session, Batch, (e.batch_id for e in experiments))
    authors = people(session, (e.created_by for e in experiments))
    configs = grouped_by(
        session,
        ExperimentAgentConfig,
        ExperimentAgentConfig.experiment_id,
        ids,
        col(ExperimentAgentConfig.id),
    )
    executions = grouped_by(
        session,
        ExperimentExecution,
        ExperimentExecution.experiment_id,
        ids,
        col(ExperimentExecution.started_at).desc(),
    )
    return [
        _experiment_response(
            experiment,
            dataset=datasets.get(experiment.dataset_id),
            batch=batches.get(experiment.batch_id),
            author=authors.get(experiment.created_by),
            experiment_configs=configs[experiment.id],
            executions=executions[experiment.id],
        )
        for experiment in experiments
    ]


def _build_experiment_response(
    experiment: Experiment, session: Session
) -> ExperimentResponse:
    return _build_experiment_responses([experiment], session)[0]


def _experiment_response(
    experiment: Experiment,
    *,
    dataset: Dataset | None,
    batch: Batch | None,
    author: PersonResponse | None,
    experiment_configs: list[ExperimentAgentConfig],
    executions: list[ExperimentExecution],
) -> ExperimentResponse:
    """`executions` are ordered from the newest to the oldest."""
    latest_with_results = next((e for e in executions if e.results_file_path), None)
    latest_analyzable = next(
        (
            e
            for e in executions
            if e.status == "completed" and e.results_file_path
        ),
        None,
    )

    return ExperimentResponse(
        id=int(experiment.id) if experiment.id is not None else 0,
        name=experiment.name,
        description=experiment.description,
        dataset_id=experiment.dataset_id,
        status=experiment.status,
        created_at=experiment.created_at,
        completed_at=experiment.completed_at,
        author=author,
        sampling_type=experiment.sampling_type,
        sampling_size=experiment.sampling_size,
        sampling_start_row=experiment.sampling_start_row,
        sampling_end_row=experiment.sampling_end_row,
        sampling_seed=batch.sampling_seed
        if batch and batch.sampling_seed is not None
        else experiment.sampling_seed,
        batch_id=experiment.batch_id,
        batch_name=batch.name if batch else None,
        variant=parse_point(experiment.variant) or None,
        row_count=execution_row_count(latest_with_results)
        if latest_with_results
        else None,
        last_run_at=executions[0].started_at if executions else None,
        latest_analyzable_execution_id=latest_analyzable.id
        if latest_analyzable
        else None,
        **latest_figures(executions),
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
                step_key=config.step_key,
                label=config.label,
                prompt_version_id=config.prompt_version_id,
                model_id=config.model_id,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                execution_order=config.execution_order,
                is_active=config.is_active,
                input_mappings=json.loads(config.input_mappings)
                if config.input_mappings
                else None,
                formulas=json.loads(config.formulas) if config.formulas else None,
                created_at=config.created_at,
            )
            for config in experiment_configs
        ],
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/experiments", response_model=list[ExperimentResponse])
def list_experiments(session: SessionDep):
    """Get all experiments"""
    experiments = session.exec(
        select(Experiment).order_by(Experiment.created_at.desc())
    ).all()
    return _build_experiment_responses(list(experiments), session)


@router.post("/experiments", response_model=ExperimentResponse, status_code=201)
def create_experiment(
    exp_data: ExperimentCreate, session: SessionDep
):
    """Create a new experiment and automatically start it."""
    try:
        experiment = add_experiment(session, exp_data)
    except ExperimentConfigError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    session.commit()
    session.refresh(experiment)

    experiment_id = int(experiment.id) if experiment.id is not None else 0
    try:
        outcome = async_jobs.start_experiment(
            experiment_id,
            current_workspace_id(session),
            launched_by=current_user_id(session),
        )
        logger.info("Experiment %s dispatched (%s)", experiment_id, outcome)
    except Exception:
        logger.exception("Failed to start experiment %s", experiment_id)
    # A full workspace queues the run: the response must say so
    session.refresh(experiment)

    return _build_experiment_response(experiment, session)


@router.get("/experiments/{exp_id}", response_model=ExperimentResponse)
def get_experiment(exp_id: int, session: SessionDep):
    """Get a specific experiment with all its configurations."""
    experiment = session.get(Experiment, exp_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return _build_experiment_response(experiment, session)


@router.delete("/experiments/{exp_id}", status_code=204)
def delete_experiment(exp_id: int, session: SessionDep):
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

    clear_item_links(session, "experiment", exp_id)
    session.delete(experiment)
    session.commit()


@router.post("/experiments/{exp_id}/resample", response_model=ExperimentResponse)
def resample_experiment(
    exp_id: int, session: SessionDep
):
    """Draw a new random sample: the next run takes other rows than the previous ones.

    Runs already made keep the seed they ran with. The experiments of a batch share
    the batch's sample, which is not redrawn from one of them.
    """
    experiment = session.get(Experiment, exp_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if experiment.sampling_type != "random":
        raise HTTPException(
            status_code=400, detail="Only a random sample can be redrawn"
        )
    if experiment.batch_id is not None:
        raise HTTPException(
            status_code=409,
            detail="The sample of a batch is shared by its experiments",
        )

    experiment.sampling_seed = secrets.randbelow(2**32)
    session.add(experiment)
    session.commit()
    session.refresh(experiment)
    return _build_experiment_response(experiment, session)


@router.post("/experiments/{experiment_id}/cancel")
def cancel_experiment(experiment_id: int) -> ExperimentCancelResponse:
    """Cancel a running experiment task."""
    return ExperimentCancelResponse(
        experiment_id=experiment_id,
        cancelled=async_jobs.cancel_experiment(experiment_id),
    )


@router.post("/experiments/{experiment_id}/rerun")
def rerun_experiment(
    experiment_id: int, session: SessionDep
) -> ExperimentRerunResponse:
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
        outcome = async_jobs.start_experiment(
            experiment_id,
            current_workspace_id(session),
            launched_by=current_user_id(session),
        )
        return ExperimentRerunResponse(
            experiment_id=experiment_id,
            message="Experiment re-run "
            + ("queued" if outcome == "queued" else "started successfully"),
            status=outcome,
        )
    except Exception as e:
        logger.exception("Failed to start experiment %s", experiment_id)
        raise HTTPException(
            status_code=500, detail="Failed to start the experiment re-run"
        ) from e
