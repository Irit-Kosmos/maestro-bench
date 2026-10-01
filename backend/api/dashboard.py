"""
API router for the dashboard: recent activity in a single request.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session, col, func, select

from db import get_session
from results_files import execution_row_count
from schemas.dashboard import (
    DashboardActivity,
    DashboardExperiment,
    DashboardResponse,
)
from tables import (
    AgentExecutionSnapshot,
    Batch,
    Dataset,
    Experiment,
    ExperimentAgentConfig,
    ExperimentExecution,
    Model,
)

router = APIRouter(tags=["dashboard"])

ACTIVITY_DAYS = 7
RECENT_LIMIT = 5


def _distinct(names: list[str]) -> list[str]:
    """Names without repeats, in the order they first appear."""
    return list(dict.fromkeys(names))


def _models(
    experiment: Experiment, execution: ExperimentExecution | None, session: Session
) -> list[str]:
    """Models the pipeline ran with, or will run with while nothing has executed yet."""
    if execution:
        snapshots = session.exec(
            select(AgentExecutionSnapshot.model_name_snapshot)
            .where(AgentExecutionSnapshot.execution_id == execution.id)
            .order_by(col(AgentExecutionSnapshot.execution_order))
        ).all()
        if snapshots:
            return _distinct(list(snapshots))

    configured = session.exec(
        select(Model.name)
        .join(ExperimentAgentConfig, col(ExperimentAgentConfig.model_id) == col(Model.id))
        .where(
            ExperimentAgentConfig.experiment_id == experiment.id,
            col(ExperimentAgentConfig.is_active).is_(True),
        )
        .order_by(col(ExperimentAgentConfig.execution_order))
    ).all()
    return _distinct(list(configured))


def _recent_experiment(experiment: Experiment, session: Session) -> DashboardExperiment:
    dataset = session.get(Dataset, experiment.dataset_id)
    batch = session.get(Batch, experiment.batch_id) if experiment.batch_id else None
    execution = session.exec(
        select(ExperimentExecution)
        .where(ExperimentExecution.experiment_id == experiment.id)
        .order_by(col(ExperimentExecution.started_at).desc())
    ).first()

    duration = None
    if execution and execution.completed_at:
        duration = (execution.completed_at - execution.started_at).total_seconds()

    return DashboardExperiment(
        id=int(experiment.id) if experiment.id is not None else 0,
        name=experiment.name,
        status=experiment.status,
        created_at=experiment.created_at,
        batch_id=experiment.batch_id,
        batch_name=batch.name if batch else None,
        dataset_name=dataset.name if dataset else None,
        models=_models(experiment, execution, session),
        row_count=execution_row_count(execution) if execution else None,
        duration_seconds=duration,
        total_tokens=execution.total_tokens if execution else None,
        total_cost_usd=execution.total_cost_usd if execution else None,
    )


def _activity(session: Session) -> DashboardActivity:
    # The database stores naive UTC datetimes
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=ACTIVITY_DAYS)

    experiments = session.exec(
        select(func.count()).select_from(Experiment).where(Experiment.created_at >= since)
    ).one()
    tokens, cost = session.exec(
        select(
            func.coalesce(func.sum(ExperimentExecution.total_tokens), 0),
            func.coalesce(func.sum(ExperimentExecution.total_cost_usd), 0.0),
        ).where(ExperimentExecution.started_at >= since)
    ).one()
    active = session.exec(
        select(func.count())
        .select_from(Experiment)
        .where(col(Experiment.status).in_(("pending", "running")))
    ).one()

    return DashboardActivity(
        days=ACTIVITY_DAYS,
        experiments=experiments,
        total_tokens=int(tokens),
        total_cost_usd=round(float(cost), 6),
        active=active,
    )


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(session: Annotated[Session, Depends(get_session)]):
    """Recent experiments with their cost and timing, and the last week's activity."""
    recent = session.exec(
        select(Experiment).order_by(col(Experiment.created_at).desc()).limit(RECENT_LIMIT)
    ).all()
    return DashboardResponse(
        activity=_activity(session),
        recent_experiments=[_recent_experiment(exp, session) for exp in recent],
    )
