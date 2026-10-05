"""Invitation links: one person joins a workspace with a role, once, before it expires."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from sqlmodel import Session, select

import config
from auth.workspaces import MembershipError, set_member
from tables import Invitation, Membership, User, Workspace

# An invitation never makes an owner: that is a decision for an owner to take later
INVITABLE_ROLES = ("viewer", "editor")


class InvitationError(ValueError):
    """The link cannot be used. It never says why: a wrong, used, revoked or expired
    link look the same to whoever holds it."""


@dataclass(frozen=True)
class Accepted:
    workspace: Workspace
    role: str
    joined: bool  # False when the user already belonged to the workspace


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def _is_past(moment: datetime) -> bool:
    """Moments come back from the database without a time zone: they are UTC."""
    return (moment if moment.tzinfo else moment.replace(tzinfo=UTC)) <= _now()


def create_invitation(
    db: Session, workspace: Workspace, role: str, user_id: int
) -> tuple[Invitation, str]:
    """Make an invitation; the token is returned once and only its hash is kept."""
    if role not in INVITABLE_ROLES:
        raise InvitationError(f"An invitation gives one of: {', '.join(INVITABLE_ROLES)}")
    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        workspace_id=workspace.id,
        token_hash=_hash(token),
        role=role,
        created_by=user_id,
        expires_at=_now() + timedelta(days=config.INVITATION_DAYS),
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
                Invitation.used_at.is_(None),
                Invitation.revoked_at.is_(None),
                Invitation.expires_at > _now(),
            )
            .order_by(Invitation.created_at.desc())
        ).all()
    )


def revoke(db: Session, workspace_id: int, invitation_id: int) -> bool:
    result = db.execute(
        update(Invitation)
        .where(
            Invitation.id == invitation_id,
            Invitation.workspace_id == workspace_id,
            Invitation.used_at.is_(None),
            Invitation.revoked_at.is_(None),
        )
        .values(revoked_at=_now())
    )
    db.commit()
    return result.rowcount > 0


def revoke_all(db: Session, workspace_id: int) -> None:
    db.execute(
        update(Invitation)
        .where(
            Invitation.workspace_id == workspace_id,
            Invitation.used_at.is_(None),
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
        or invitation.used_at is not None
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
    """Join the workspace of an invitation, using the invitation up.

    Someone who already belongs to it keeps their role and the invitation stays valid.
    """
    invitation = _usable(db, token)
    workspace = db.get(Workspace, invitation.workspace_id)
    if workspace.archived_at is not None:
        raise InvitationError("This workspace is archived")

    membership = db.get(Membership, (workspace.id, user.id))
    if membership is not None:
        return Accepted(workspace, membership.role, joined=False)

    # Several people opening the same link at once: only one update can win
    claimed = db.execute(
        update(Invitation)
        .where(Invitation.id == invitation.id, Invitation.used_at.is_(None))
        .values(used_at=_now(), used_by=user.id)
    )
    if claimed.rowcount == 0:
        db.rollback()
        raise InvitationError("This invitation is invalid or has expired")
    try:
        set_member(db, workspace, user, invitation.role)
    except MembershipError as e:  # pragma: no cover - the role was checked on creation
        db.rollback()
        raise InvitationError(str(e)) from e
    return Accepted(workspace, invitation.role, joined=True)

