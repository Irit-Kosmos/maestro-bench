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
API router for the workspaces the signed-in user belongs to.

The data inside a workspace lives under `/workspaces/{slug}/...` (see main.py).
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

import workspace_lifecycle
from auth import invitations
from auth.deps import CurrentUser, get_engine, require_user
from auth.workspaces import (
    ROLES,
    MembershipError,
    WorkspaceContext,
    allows_archived,
    can_create_workspace,
    create_workspace,
    remove_member,
    requires,
    set_member,
    workspace_context,
)
from tables import Invitation, Membership, User, Workspace

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceOut(BaseModel):
    slug: str
    name: str
    role: str  # the signed-in user's role in it
    archived: bool


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


def _out(workspace: Workspace, role: str) -> WorkspaceOut:
    return WorkspaceOut(
        slug=workspace.slug,
        name=workspace.name,
        role=role,
        archived=workspace.archived_at is not None,
    )


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(
    user: Annotated[CurrentUser, Depends(require_user)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    """The workspaces the user belongs to, by name."""
    with Session(engine) as db:
        rows = db.exec(
            select(Workspace, Membership.role)
            .join(Membership, col(Membership.workspace_id) == col(Workspace.id))
            .where(Membership.user_id == user.id)
        ).all()
    return [
        _out(workspace, role)
        for workspace, role in sorted(rows, key=lambda r: r[0].name.lower())
    ]


@router.post("", response_model=WorkspaceOut, status_code=201)
def new_workspace(
    data: WorkspaceCreate,
    user: Annotated[CurrentUser, Depends(require_user)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    """Create a workspace; its creator is its owner."""
    if not can_create_workspace(user):
        raise HTTPException(403, "Only instance administrators can create workspaces")
    name = data.name.strip()
    if not name:
        raise HTTPException(422, "A workspace needs a name")
    with Session(engine) as db:
        return _out(create_workspace(db, name, user.id), "owner")


@router.get("/{slug}", response_model=WorkspaceOut)
def get_workspace(context: Annotated[WorkspaceContext, Depends(workspace_context)]):
    return WorkspaceOut(
        slug=context.slug,
        name=context.name,
        role=context.role,
        archived=context.archived,
    )


@router.patch("/{slug}", response_model=WorkspaceOut)
@requires("owner")
def rename_workspace(
    data: WorkspaceUpdate,
    context: Annotated[WorkspaceContext, Depends(workspace_context)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    name = data.name.strip()
    if not name:
        raise HTTPException(422, "A workspace needs a name")
    with Session(engine) as db:
        workspace = db.get(Workspace, context.id)
        workspace.name = name
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
        return _out(workspace, context.role)


# ---------------------------------------------------------------------------
# Archiving and deleting
# ---------------------------------------------------------------------------


def _workspace(db: Session, context: WorkspaceContext) -> Workspace:
    return db.get(Workspace, context.id)


@router.post("/{slug}/archive", response_model=WorkspaceOut)
@requires("owner")
def archive_workspace(
    context: Annotated[WorkspaceContext, Depends(workspace_context)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    """Make the workspace read-only: its runs stop, its API keys and invitations go."""
    with Session(engine) as db:
        workspace = _workspace(db, context)
        workspace_lifecycle.archive(db, workspace)
        return _out(workspace, context.role)


@router.post("/{slug}/unarchive", response_model=WorkspaceOut)
@allows_archived
@requires("owner")
def unarchive_workspace(
    context: Annotated[WorkspaceContext, Depends(workspace_context)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    with Session(engine) as db:
        workspace = _workspace(db, context)
        workspace_lifecycle.unarchive(db, workspace)
        return _out(workspace, context.role)


@router.delete("/{slug}", status_code=204)
@allows_archived
@requires("owner")
def delete_workspace(
    confirm: str,
    context: Annotated[WorkspaceContext, Depends(workspace_context)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    """Delete an archived workspace and everything in it. `confirm` repeats its slug."""
    if not context.archived:
        raise HTTPException(409, "Archive the workspace before deleting it")
    if confirm != context.slug:
        raise HTTPException(422, "The confirmation does not match the workspace")
    with Session(engine) as db:
        workspace_lifecycle.delete_workspace(db, _workspace(db, context))


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


class MemberOut(BaseModel):
    user_id: int
    display_name: str
    email: str | None
    avatar_url: str | None
    role: str
    joined_at: datetime


class MemberAdd(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: str


class MemberUpdate(BaseModel):
    role: str


def _check_role(role: str) -> None:
    if role not in ROLES:
        raise HTTPException(422, f"Unknown role {role!r}: use one of {', '.join(ROLES)}")


def _member_out(membership: Membership, user: User) -> MemberOut:
    return MemberOut(
        user_id=user.id,
        display_name=user.display_name,
        email=user.email,
        avatar_url=user.avatar_url,
        role=membership.role,
        joined_at=membership.created_at,
    )


def _membership_error(error: MembershipError) -> HTTPException:
    return HTTPException(409, str(error))


@router.get("/{slug}/members", response_model=list[MemberOut])
def list_members(
    context: Annotated[WorkspaceContext, Depends(workspace_context)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    """Everyone in the workspace, owners first."""
    with Session(engine) as db:
        rows = db.exec(
            select(Membership, User)
            .join(User, col(User.id) == col(Membership.user_id))
            .where(Membership.workspace_id == context.id)
        ).all()
    members = [_member_out(m, u) for m, u in rows]
    return sorted(
        members, key=lambda m: (-ROLES.index(m.role), m.display_name.lower(), m.user_id)
    )


@router.post("/{slug}/members", response_model=MemberOut, status_code=201)
@requires("owner")
def add_member(
    data: MemberAdd,
    context: Annotated[WorkspaceContext, Depends(workspace_context)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    """Add someone who has already signed in once, found by their email."""
    _check_role(data.role)
    email = data.email.strip().lower()
    with Session(engine) as db:
        users = db.exec(
            select(User).where(func.lower(User.email) == email, col(User.is_active))
        ).all()
        if not users:
            raise HTTPException(
                404,
                "Nobody with this email has signed in yet: send them an invitation link",
            )
        if len(users) > 1:
            raise HTTPException(
                409, "Several accounts share this email: send an invitation link instead"
            )
        user = users[0]
        if db.get(Membership, (context.id, user.id)) is not None:
            raise HTTPException(409, "This user is already in the workspace")
        set_member(db, _workspace(db, context), user, data.role)
        return _member_out(db.get(Membership, (context.id, user.id)), user)


@router.put("/{slug}/members/{user_id}", response_model=MemberOut)
@requires("owner")
def change_member_role(
    user_id: int,
    data: MemberUpdate,
    context: Annotated[WorkspaceContext, Depends(workspace_context)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    _check_role(data.role)
    with Session(engine) as db:
        user = db.get(User, user_id)
        if user is None or db.get(Membership, (context.id, user_id)) is None:
            raise HTTPException(404, "This user is not in the workspace")
        try:
            set_member(db, _workspace(db, context), user, data.role)
        except MembershipError as e:
            raise _membership_error(e) from e
        return _member_out(db.get(Membership, (context.id, user_id)), user)


@router.delete("/{slug}/members/{user_id}", status_code=204)
@allows_archived
@requires("viewer")
def remove_workspace_member(
    user_id: int,
    context: Annotated[WorkspaceContext, Depends(workspace_context)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    """Remove someone (an owner's call), or leave the workspace yourself."""
    if user_id != context.user_id and not context.can("owner"):
        raise HTTPException(403, "This needs the owner role in this workspace")
    with Session(engine) as db:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(404, "This user is not in the workspace")
        try:
            remove_member(db, _workspace(db, context), user)
        except MembershipError as e:
            if "not a member" in str(e):
                raise HTTPException(404, "This user is not in the workspace") from e
            raise _membership_error(e) from e


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


class InvitationCreate(BaseModel):
    role: str
    # 1, 7 or 30; null keeps the link open until it is revoked
    days: int | None = 7


class InvitationOut(BaseModel):
    id: int
    role: str
    created_at: datetime
    expires_at: datetime | None
    uses: int


class InvitationCreated(InvitationOut):
    # Shown once: only a hash of it is kept
    token: str


def _invitation_out(invitation: Invitation) -> InvitationOut:
    return InvitationOut(
        id=invitation.id,
        role=invitation.role,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
        uses=invitation.uses,
    )


@router.get("/{slug}/invitations", response_model=list[InvitationOut])
@requires("owner")
def list_invitations(
    context: Annotated[WorkspaceContext, Depends(workspace_context)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    """The invitations that can still be used."""
    with Session(engine) as db:
        return [_invitation_out(i) for i in invitations.pending(db, context.id)]


@router.post("/{slug}/invitations", response_model=InvitationCreated, status_code=201)
@requires("owner")
def create_invitation(
    data: InvitationCreate,
    context: Annotated[WorkspaceContext, Depends(workspace_context)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    """Make a link that gives `role` (viewer or editor) to whoever opens it, for `days`."""
    with Session(engine) as db:
        try:
            invitation, token = invitations.create_invitation(
                db, _workspace(db, context), data.role, context.user_id, data.days
            )
        except invitations.InvitationError as e:
            raise HTTPException(422, str(e)) from e
        return InvitationCreated(**_invitation_out(invitation).model_dump(), token=token)


@router.delete("/{slug}/invitations/{invitation_id}", status_code=204)
@requires("owner")
def revoke_invitation(
    invitation_id: int,
    context: Annotated[WorkspaceContext, Depends(workspace_context)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    with Session(engine) as db:
        if not invitations.revoke(db, context.id, invitation_id):
            raise HTTPException(404, "No such invitation")
