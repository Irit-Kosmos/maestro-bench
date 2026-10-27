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
