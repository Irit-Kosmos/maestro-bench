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
API router for instance administrators: what they can see of the instance.

Every field these endpoints return is declared, with the task it serves, in
admin/fields.py; `GET /admin/visibility` hands that list to every signed-in user.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.engine import Engine
from sqlmodel import Session

from admin import fields, queries
from auth.deps import CurrentUser, get_engine, require_user

router = APIRouter(prefix="/admin", tags=["admin"])


def require_instance_admin(
    user: Annotated[CurrentUser, Depends(require_user)],
) -> CurrentUser:
    if not user.is_instance_admin:
        raise HTTPException(403, "Only instance administrators can see this")
    return user


AdminDep = Annotated[CurrentUser, Depends(require_instance_admin)]
EngineDep = Annotated[Engine, Depends(get_engine)]


class AccountOut(BaseModel):
    id: int
    email: str | None
    active: bool
    last_sign_in_on: date | None
    workspace_count: int


class MonthUsageOut(BaseModel):
    month: str  # YYYY-MM
    tokens: int
    cost_usd: float
    unknown_source_tokens: int
    unknown_source_cost_usd: float


class WorkspaceOut(BaseModel):
    slug: str
    name: str
    owner_emails: list[str]
    member_count: int
    created_on: date | None
    archived: bool
    last_activity_on: date | None
    disk_bytes: int
    usage: list[MonthUsageOut]


class HealthOut(BaseModel):
    running_executions: int
    max_concurrent_executions: int
    failed_last_24h: int


@router.get("/visibility")
def visibility(_: Annotated[CurrentUser, Depends(require_user)]):
    """What administrators can see and why: open to every signed-in user."""
    return fields.disclosure()


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(_: AdminDep, engine: EngineDep):
    with Session(engine) as db:
        return queries.accounts(db)


@router.get("/workspaces", response_model=list[WorkspaceOut])
def list_workspaces(_: AdminDep, engine: EngineDep):
    with Session(engine) as db:
        return queries.workspaces(db)


@router.get("/health", response_model=HealthOut)
def instance_health(_: AdminDep, engine: EngineDep):
    with Session(engine) as db:
        return queries.health(db)
