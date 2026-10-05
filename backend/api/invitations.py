"""
API router for opening an invitation link. The person holding it is not in the
workspace yet, so this lives outside `/workspaces/{slug}`.

The token travels in the body, never in the URL: URLs end up in access logs.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine
from sqlmodel import Session

from auth import invitations
from auth.deps import CurrentUser, get_engine, require_user
from tables import User

router = APIRouter(prefix="/invitations", tags=["invitations"])


class TokenIn(BaseModel):
    token: str = Field(min_length=1, max_length=200)


class InvitationPreview(BaseModel):
    workspace_name: str
    role: str
    invited_by: str | None


class InvitationAccepted(BaseModel):
    slug: str
    name: str
    role: str
    joined: bool


@router.post("/preview", response_model=InvitationPreview)
def preview_invitation(
    data: TokenIn,
    _user: Annotated[CurrentUser, Depends(require_user)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    """What the link offers, so that the person can decide to accept."""
    with Session(engine) as db:
        try:
            invitation, workspace, inviter = invitations.preview(db, data.token)
        except invitations.InvitationError as e:
            raise HTTPException(404, str(e)) from e
        return InvitationPreview(
            workspace_name=workspace.name,
            role=invitation.role,
            invited_by=inviter.display_name if inviter else None,
        )


@router.post("/accept", response_model=InvitationAccepted)
def accept_invitation(
    data: TokenIn,
    current: Annotated[CurrentUser, Depends(require_user)],
    engine: Annotated[Engine, Depends(get_engine)],
):
    with Session(engine) as db:
        try:
            accepted = invitations.accept(db, data.token, db.get(User, current.id))
        except invitations.InvitationError as e:
            raise HTTPException(404, str(e)) from e
        return InvitationAccepted(
            slug=accepted.workspace.slug,
            name=accepted.workspace.name,
            role=accepted.role,
            joined=accepted.joined,
        )
