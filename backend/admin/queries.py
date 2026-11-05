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
The only place that reads across workspaces, for instance administrators.

Every other request works on a session confined to one workspace (see
workspace_scope.py). These queries need the whole instance, so they run on an
unscoped session, and they only ever compute what admin/fields.py declares:
counts, sums, sizes and days. They never read the names or content of what a
workspace holds.
"""

import os
from contextlib import suppress
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import func
from sqlmodel import Session, col, select

import config
import workspace_files
from admin.fields import USAGE_MONTHS
from tables import (
    AgentExecutionSnapshot,
    ExperimentExecution,
    Membership,
    User,
    Workspace,
)
from workspace_scope import is_scoped

INSTANCE_KEY = "instance"


def _unscoped(db: Session) -> Session:
    if is_scoped(db):
        raise RuntimeError("Administration queries need a session that is not scoped")
    return db


def _day(moment: datetime | None) -> date | None:
    return moment.astimezone(UTC).date() if moment else None


def accounts(db: Session) -> list[dict]:
    db = _unscoped(db)
    counts = dict(
        db.exec(
            select(Membership.user_id, func.count()).group_by(Membership.user_id)
        ).all()
    )
    users = db.exec(
        select(User.id, User.email, User.is_active, User.last_login_at).order_by(
            func.lower(func.coalesce(User.email, "")), User.id
        )
    ).all()
    return [
        {
            "id": user_id,
            "email": email,
            "active": active,
            "last_sign_in_on": _day(last_login),
            "workspace_count": counts.get(user_id, 0),
        }
        for user_id, email, active, last_login in users
    ]


def _months(today: date) -> list[date]:
    """The first day of the last USAGE_MONTHS months, the current one first."""
    first = today.replace(day=1)
    months = [first]
    for _ in range(USAGE_MONTHS - 1):
        first = (first - timedelta(days=1)).replace(day=1)
        months.append(first)
    return months


def _usage(db: Session, months: list[date]) -> dict[tuple[int, date], dict]:
    """Tokens and cost of the steps the instance's keys paid, per workspace and month."""
    since = datetime.combine(months[-1], datetime.min.time(), tzinfo=UTC)
    month = func.date_trunc(
        "month", func.timezone("UTC", ExperimentExecution.started_at)
    )
    rows = db.exec(
        select(
            AgentExecutionSnapshot.workspace_id,
            month,
            func.coalesce(func.sum(AgentExecutionSnapshot.total_tokens), 0),
            func.coalesce(func.sum(AgentExecutionSnapshot.total_cost_usd), 0.0),
        )
        .join(
            ExperimentExecution,
            col(ExperimentExecution.id) == col(AgentExecutionSnapshot.execution_id),
        )
        .where(ExperimentExecution.started_at >= since)
        # Only what the instance paid for: a workspace's own key is none of its
        # business, and a step that did not record whose key paid may have used it
        .where(AgentExecutionSnapshot.key_source == INSTANCE_KEY)
        .group_by(AgentExecutionSnapshot.workspace_id, month)
    ).all()
    return {
        (workspace_id, started.date()): {"tokens": int(tokens), "cost_usd": float(cost)}
        for workspace_id, started, tokens, cost in rows
    }


def _empty_month() -> dict:
    return {"tokens": 0, "cost_usd": 0.0}


def disk_bytes(workspace_id: int) -> int:
    """The size of the files a workspace keeps on disk (its datasets and results)."""
    total = 0
    root: Path = workspace_files.workspace_dir(workspace_id)
    for folder, _, files in os.walk(root):
        for name in files:
            path = os.path.join(folder, name)
            # A file removed meanwhile counts for nothing
            if not os.path.islink(path):
                with suppress(OSError):
                    total += os.path.getsize(path)
    return total


def workspaces(db: Session, today: date | None = None) -> list[dict]:
    db = _unscoped(db)
    months = _months(today or datetime.now(UTC).date())
    member_counts = dict(
        db.exec(
            select(Membership.workspace_id, func.count()).group_by(
                Membership.workspace_id
            )
        ).all()
    )
    owners: dict[int, list[str]] = {}
    for workspace_id, email in db.exec(
        select(Membership.workspace_id, User.email)
        .join(User, col(User.id) == col(Membership.user_id))
        .where(Membership.role == "owner")
        .order_by(func.lower(func.coalesce(User.email, "")))
    ).all():
        if email:
            owners.setdefault(workspace_id, []).append(email)
    last_activity = dict(
        db.exec(
            select(
                ExperimentExecution.workspace_id,
                func.max(ExperimentExecution.started_at),
            ).group_by(ExperimentExecution.workspace_id)
        ).all()
    )
    usage = _usage(db, months)
    rows = db.exec(
        select(
            Workspace.id,
            Workspace.slug,
            Workspace.name,
            Workspace.created_at,
            Workspace.archived_at,
        ).order_by(func.lower(Workspace.name), Workspace.id)
    ).all()
    return [
        {
            "slug": slug,
            "name": name,
            "owner_emails": owners.get(workspace_id, []),
            "member_count": member_counts.get(workspace_id, 0),
            "created_on": _day(created),
            "archived": archived is not None,
            "last_activity_on": _day(last_activity.get(workspace_id)),
            "disk_bytes": disk_bytes(workspace_id),
            "usage": [
                {
                    "month": month.strftime("%Y-%m"),
                    **{
                        key: round(value, 6) if isinstance(value, float) else value
                        for key, value in usage.get(
                            (workspace_id, month), _empty_month()
                        ).items()
                    },
                }
                for month in months
            ],
        }
        for workspace_id, slug, name, created, archived in rows
    ]


def health(db: Session) -> dict:
    db = _unscoped(db)
    since = datetime.now(UTC) - timedelta(hours=24)
    running = db.exec(
        select(func.count())
        .select_from(ExperimentExecution)
        .where(ExperimentExecution.status == "running")
    ).one()
    failed = db.exec(
        select(func.count())
        .select_from(ExperimentExecution)
        .where(ExperimentExecution.status == "failed")
        .where(
            func.coalesce(
                ExperimentExecution.completed_at, ExperimentExecution.started_at
            )
            >= since
        )
    ).one()
    return {
        "running_executions": running,
        "max_concurrent_executions": config.MAX_CONCURRENT_EXPERIMENTS,
        "failed_last_24h": failed,
    }
