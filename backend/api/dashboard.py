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
API router for the dashboard: recent activity in a single request.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from sqlmodel import Session, col, func, select

from db import SessionDep
from loading import by_id, grouped_by
from results_files import execution_row_count
from schemas.dashboard import (
    DashboardActiveExperiment,
    DashboardActivity,
    DashboardBucket,
    DashboardExperiment,
    DashboardModel,
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
    "24h": timedelta(hours=2),
    "7d": timedelta(hours=12),
    "30d": timedelta(days=2),
    "90d": timedelta(days=6),
}
# "all" has no fixed length: it is cut in about this many slices
BUCKET_TARGET = 15
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


def _distinct(models: list[DashboardModel]) -> list[DashboardModel]:
    """Models without repeats, in the order they first appear."""
    return list({(m.name, m.provider): m for m in models}.values())


def _models_of(
    experiments: list[Experiment],
    latest: dict[int, ExperimentExecution],
    session: Session,
) -> dict[int, list[DashboardModel]]:
    """Models each pipeline ran with, or will run with while nothing has executed yet."""
    snapshots_of: dict[int, list[tuple[str, str]]] = defaultdict(list)
    if latest:
        for execution_id, name, provider in session.exec(
            select(
                AgentExecutionSnapshot.execution_id,
                AgentExecutionSnapshot.model_name_snapshot,
                AgentExecutionSnapshot.model_provider_snapshot,
            )
            .where(
                col(AgentExecutionSnapshot.execution_id).in_(
                    [e.id for e in latest.values()]
                )
            )
            .order_by(col(AgentExecutionSnapshot.execution_order))
        ).all():
            snapshots_of[execution_id].append((name, provider))

    models: dict[int, list[DashboardModel]] = {}
    unexecuted: list[int] = []
    for experiment in experiments:
        execution = latest.get(experiment.id)
        snapshots = snapshots_of[execution.id] if execution else []
        if snapshots:
            # Aggregators have no model
            models[experiment.id] = _distinct(
                [DashboardModel(name=n, provider=p) for n, p in snapshots if n]
            )
        else:
            unexecuted.append(experiment.id)

    configured: dict[int, list[DashboardModel]] = defaultdict(list)
    if unexecuted:
        for experiment_id, name, provider in session.exec(
            select(ExperimentAgentConfig.experiment_id, Model.name, Model.provider)
            .join(
                Model, col(ExperimentAgentConfig.model_id) == col(Model.id)
            )
            .where(
                col(ExperimentAgentConfig.experiment_id).in_(unexecuted),
                col(ExperimentAgentConfig.is_active).is_(True),
            )
            .order_by(col(ExperimentAgentConfig.execution_order))
        ).all():
            configured[experiment_id].append(DashboardModel(name=name, provider=provider))
    for experiment_id in unexecuted:
        models[experiment_id] = _distinct(configured[experiment_id])
    return models


def _recent_experiments(
    experiments: list[Experiment], session: Session
) -> list[DashboardExperiment]:
    datasets = by_id(session, Dataset, (e.dataset_id for e in experiments))
    batches = by_id(session, Batch, (e.batch_id for e in experiments))
    executions = grouped_by(
        session,
        ExperimentExecution,
        ExperimentExecution.experiment_id,
        [e.id for e in experiments if e.id is not None],
        col(ExperimentExecution.started_at).desc(),
    )
    latest = {
        experiment_id: found[0] for experiment_id, found in executions.items() if found
    }
    models = _models_of(experiments, latest, session)

    recent = []
    for experiment in experiments:
        execution = latest.get(experiment.id)
        dataset = datasets.get(experiment.dataset_id)
        batch = batches.get(experiment.batch_id)
        duration = None
        if execution and execution.completed_at:
            duration = (execution.completed_at - execution.started_at).total_seconds()
        recent.append(
            DashboardExperiment(
                id=int(experiment.id) if experiment.id is not None else 0,
                name=experiment.name,
                status=experiment.status,
                created_at=experiment.created_at,
                batch_id=experiment.batch_id,
                batch_name=batch.name if batch else None,
                dataset_name=dataset.name if dataset else None,
                models=models[experiment.id],
                row_count=execution_row_count(execution) if execution else None,
                duration_seconds=duration,
                total_tokens=execution.total_tokens if execution else None,
                total_cost_usd=execution.total_cost_usd if execution else None,
            )
        )
    return recent


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
    now = datetime.now(UTC)
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
            ExperimentExecution.id,
            ExperimentExecution.experiment_id,
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
    # The latest execution of each experiment in each stretch: an experiment is
    # affected when the run it ended the stretch on went wrong
    latest_in: dict[int, dict[int, tuple[datetime, int, bool]]] = defaultdict(dict)
    for (
        execution_id,
        experiment_id,
        started_at,
        status,
        tokens,
        cost,
        rows_done,
        rows_failed,
    ) in executions:
        has_failures = status not in ("cancelled", "interrupted") and (
            status == "failed" or rows_failed > 0
        )
        for totals in totals_at(started_at):
            totals.total_tokens += tokens or 0
            totals.total_cost_usd += cost or 0.0
            totals.rows_done += rows_done
            totals.rows_failed += rows_failed
            latest = latest_in[id(totals)]
            known = latest.get(experiment_id)
            if known is None or (started_at, execution_id) > known[:2]:
                latest[experiment_id] = (started_at, execution_id, has_failures)

    for totals in (current, previous, *buckets):
        if totals is not None:
            totals.total_cost_usd = round(totals.total_cost_usd, 6)
            totals.experiments_with_failures = sum(
                failed for _, _, failed in latest_in[id(totals)].values()
            )

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
    session: SessionDep,
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
        recent_experiments=_recent_experiments(list(recent), session),
    )
