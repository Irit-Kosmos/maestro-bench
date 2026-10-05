"""
API router for the dashboard: recent activity in a single request.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, col, func, select

from db import get_session
from results_files import execution_row_count
from schemas.dashboard import (
    DashboardActiveExperiment,
    DashboardActivity,
    DashboardBucket,
    DashboardExperiment,
    DashboardResponse,
    DashboardTotals,
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

RECENT_LIMIT = 5

# Periods the activity can cover, and how finely each is cut for its sparklines
PERIODS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}
BUCKET_SIZES = {
    "24h": timedelta(hours=1),
    "7d": timedelta(hours=6),
    "30d": timedelta(days=1),
    "90d": timedelta(days=3),
}
# "all" has no fixed length: it is cut in about this many slices
BUCKET_TARGET = 30
# ...and it is compared with what it was this long ago
GROWTH_WINDOW = timedelta(days=30)

DashboardRange = Literal["24h", "7d", "30d", "90d", "all"]


@dataclass(frozen=True)
class _Window:
    start: datetime
    bucket: timedelta
    length: timedelta
    # Whether an equally long stretch before `start` is worth comparing with
    has_previous: bool = False
    # Or, for a period with no before: everything older than this, to say how much it grew since
    growth_cutoff: datetime | None = None


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
            # Aggregators have no model
            return _distinct([name for name in snapshots if name])

    configured = session.exec(
        select(Model.name)
        .join(
            ExperimentAgentConfig, col(ExperimentAgentConfig.model_id) == col(Model.id)
        )
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


def _window(range_: str, now: datetime, session: Session) -> _Window:
    if range_ in PERIODS:
        length = PERIODS[range_]
        return _Window(now - length, BUCKET_SIZES[range_], length, has_previous=True)

    # "all": from the first thing ever run, cut in about BUCKET_TARGET slices of whole days
    earliest = session.exec(select(func.min(Experiment.created_at))).one() or now
    span = max(now - earliest, timedelta(days=1))
    bucket = timedelta(days=max(1, -(-span.days // BUCKET_TARGET)))
    cutoff = now - GROWTH_WINDOW
    return _Window(
        earliest, bucket, span, growth_cutoff=cutoff if earliest < cutoff else None
    )


def _activity(range_: str, session: Session) -> DashboardActivity:
    # The database stores naive UTC datetimes
    now = datetime.now(UTC).replace(tzinfo=None)
    window = _window(range_, now, session)
    # One read covers the period and the one before it
    floor = window.start - window.length if window.has_previous else window.start

    experiments = session.exec(
        select(Experiment.created_at, Experiment.status).where(
            Experiment.created_at >= floor
        )
    ).all()
    executions = session.exec(
        select(
            ExperimentExecution.started_at,
            ExperimentExecution.status,
            ExperimentExecution.total_tokens,
            ExperimentExecution.total_cost_usd,
            ExperimentExecution.rows_done,
            ExperimentExecution.rows_failed,
        ).where(ExperimentExecution.started_at >= floor)
    ).all()

    current = DashboardTotals()
    compared = window.has_previous or window.growth_cutoff is not None
    previous = DashboardTotals() if compared else None
    count = -(-window.length // window.bucket)
    buckets = [
        DashboardBucket(start=window.start + window.bucket * i) for i in range(count)
    ]

    def totals_at(moment: datetime) -> list[DashboardTotals]:
        """Every totals a moment adds to: its period and slice, or what it is compared with."""
        targets = []
        if moment >= window.start:
            index = min(int((moment - window.start) // window.bucket), count - 1)
            targets += [current, buckets[index]]
        elif previous is not None:
            targets.append(previous)
        if (
            previous is not None
            and window.growth_cutoff
            and moment < window.growth_cutoff
        ):
            targets.append(previous)
        return targets

    for created_at, status in experiments:
        for totals in totals_at(created_at):
            totals.experiments += 1
            totals.completed += status == "completed"
            totals.failed += status == "failed"
    for started_at, status, tokens, cost, rows_done, rows_failed in executions:
        has_failures = status not in ("cancelled", "interrupted") and (
            status == "failed" or rows_failed > 0
        )
        for totals in totals_at(started_at):
            totals.total_tokens += tokens or 0
            totals.total_cost_usd += cost or 0.0
            totals.rows_done += rows_done
            totals.rows_failed += rows_failed
            totals.executions_with_failures += has_failures

    for totals in (current, previous, *buckets):
        if totals is not None:
            totals.total_cost_usd = round(totals.total_cost_usd, 6)

    active = session.exec(
        select(Experiment)
        .where(col(Experiment.status).in_(("pending", "queued", "running")))
        .order_by(col(Experiment.created_at).desc())
    ).all()

    return DashboardActivity(
        range=range_,
        since=window.start if range_ != "all" else None,
        current=current,
        previous=previous,
        buckets=buckets,
        active=[
            DashboardActiveExperiment(
                id=int(exp.id or 0), name=exp.name, status=exp.status
            )
            for exp in active
        ],
    )


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    session: Annotated[Session, Depends(get_session)],
    period: Annotated[DashboardRange, Query(alias="range")] = "7d",
):
    """Recent experiments with their cost and timing, and the activity over a period."""
    recent = session.exec(
        select(Experiment)
        .order_by(col(Experiment.created_at).desc())
        .limit(RECENT_LIMIT)
    ).all()
    return DashboardResponse(
        activity=_activity(period, session),
        recent_experiments=[_recent_experiment(exp, session) for exp in recent],
    )
