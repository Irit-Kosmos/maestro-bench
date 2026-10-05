"""
API router for the workspaces the signed-in user belongs to.

The data inside a workspace lives under `/workspaces/{slug}/...` (see main.py).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

from auth.deps import CurrentUser, get_engine, require_user
from auth.workspaces import (
    WorkspaceContext,
    can_create_workspace,
    create_workspace,
    requires,
    workspace_context,
)
from tables import Membership, Workspace

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
