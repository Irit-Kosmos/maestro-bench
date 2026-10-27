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

"""Invitation links: whoever opens one joins a workspace with a role, until it expires
or is revoked."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, update
from sqlmodel import Session, select

from auth.workspaces import MembershipError, set_member
from tables import Invitation, Membership, User, Workspace

# An invitation never makes an owner: that is a decision for an owner to take later
INVITABLE_ROLES = ("viewer", "editor")
# How long a link can be used, in days; None keeps it open until it is revoked
LIFETIMES = (1, 7, 30, None)


class InvitationError(ValueError):
    """The link cannot be used. It never says why: a wrong, revoked or expired link
    look the same to whoever holds it."""


@dataclass(frozen=True)
class Accepted:
    workspace: Workspace
    role: str
    joined: bool  # False when the user already belonged to the workspace


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def _is_past(moment: datetime | None) -> bool:
    return moment is not None and moment <= _now()


def _not_expired():
    return or_(Invitation.expires_at.is_(None), Invitation.expires_at > _now())


def create_invitation(
    db: Session, workspace: Workspace, role: str, user_id: int, days: int | None
) -> tuple[Invitation, str]:
    """Make an invitation; the token is returned once and only its hash is kept."""
    if role not in INVITABLE_ROLES:
        raise InvitationError(f"An invitation gives one of: {', '.join(INVITABLE_ROLES)}")
    if days not in LIFETIMES:
        raise InvitationError("An invitation lasts 1, 7 or 30 days, or until it is revoked")
    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        workspace_id=workspace.id,
        token_hash=_hash(token),
        role=role,
        created_by=user_id,
        expires_at=_now() + timedelta(days=days) if days is not None else None,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation, token


def pending(db: Session, workspace_id: int) -> list[Invitation]:
    return list(
        db.exec(
            select(Invitation)
            .where(
                Invitation.workspace_id == workspace_id,
                Invitation.revoked_at.is_(None),
                _not_expired(),
            )
            .order_by(Invitation.created_at.desc())
        ).all()
    )


def revoke(db: Session, workspace_id: int, invitation_id: int) -> bool:
    result = db.exec(
        update(Invitation)
        .where(
            Invitation.id == invitation_id,
            Invitation.workspace_id == workspace_id,
            Invitation.revoked_at.is_(None),
            _not_expired(),
        )
        .values(revoked_at=_now())
    )
    db.commit()
    return result.rowcount > 0


def revoke_all(db: Session, workspace_id: int) -> None:
    db.exec(
        update(Invitation)
        .where(
            Invitation.workspace_id == workspace_id,
            Invitation.revoked_at.is_(None),
        )
        .values(revoked_at=_now())
    )
    db.commit()


def _usable(db: Session, token: str) -> Invitation:
    invitation = db.exec(
        select(Invitation).where(Invitation.token_hash == _hash(token))
    ).first()
    if (
        invitation is None
        or invitation.revoked_at is not None
        or _is_past(invitation.expires_at)
    ):
        raise InvitationError("This invitation is invalid or has expired")
    return invitation


def preview(db: Session, token: str) -> tuple[Invitation, Workspace, User | None]:
    invitation = _usable(db, token)
    workspace = db.get(Workspace, invitation.workspace_id)
    inviter = db.get(User, invitation.created_by) if invitation.created_by else None
    return invitation, workspace, inviter


def accept(db: Session, token: str, user: User) -> Accepted:
    """Join the workspace of an invitation. Someone who already belongs to it keeps
    their role, and is not counted as a use of the link."""
    invitation = _usable(db, token)
    workspace = db.get(Workspace, invitation.workspace_id)
    if workspace.archived_at is not None:
        raise InvitationError("This workspace is archived")

    membership = db.get(Membership, (workspace.id, user.id))
    if membership is not None:
        return Accepted(workspace, membership.role, joined=False)

    # Counted in the database, so that people opening the link at once all count; and
    # only while it is still open, in case it was revoked in the meantime
    counted = db.exec(
        update(Invitation)
        .where(Invitation.id == invitation.id, Invitation.revoked_at.is_(None), _not_expired())
        .values(uses=Invitation.uses + 1)
    )
    if counted.rowcount == 0:
        db.rollback()
        raise InvitationError("This invitation is invalid or has expired")
    try:
        set_member(db, workspace, user, invitation.role)
    except MembershipError as e:  # pragma: no cover - the role was checked on creation
        db.rollback()
        raise InvitationError(str(e)) from e
    return Accepted(workspace, invitation.role, joined=True)

