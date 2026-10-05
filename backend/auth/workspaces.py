"""Workspaces: who belongs to which, what each role may do, and the request scope."""

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

import config
from auth.deps import SAFE_METHODS, CurrentUser, get_engine, require_user
from auth.policy import is_instance_admin
from db import get_session
from tables import Membership, User, Workspace
from workspace_scope import scope_session

logger = logging.getLogger(__name__)

# From the least to the most powerful
ROLES = ("viewer", "editor", "owner")
DEFAULT_SLUG = "default"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class MembershipError(ValueError):
    """The change would break a rule of workspace membership."""


def allows_archived(endpoint):
    """Mark a route as usable on an archived workspace, which is otherwise read-only."""
    endpoint.allows_archived = True
    return endpoint


def role_rank(role: str) -> int:
    return ROLES.index(role)


def requires(role: str):
    """Mark a route as needing at least this role, instead of the one its method implies."""

    def mark(endpoint):
        endpoint.min_role = role
        return endpoint

    return mark


@dataclass(frozen=True)
class WorkspaceContext:
    id: int
    slug: str
    name: str
    role: str
    archived: bool
    user_id: int

    def can(self, role: str) -> bool:
        return role_rank(self.role) >= role_rank(role)


def _required_role(request: Request) -> str:
    route = request.scope.get("route")
    marked = getattr(getattr(route, "endpoint", None), "min_role", None)
    if marked:
        return marked
    return "viewer" if request.method in SAFE_METHODS else "editor"


def workspace_context(
    slug: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(require_user)],
    engine: Annotated[Engine, Depends(get_engine)],
) -> WorkspaceContext:
    """The workspace of the URL, if the user belongs to it and may do what is asked.

    A workspace the user is not in looks the same as one that does not exist.
    """
    with Session(engine) as db:
        found = db.exec(
            select(Workspace, Membership.role)
            .join(Membership, col(Membership.workspace_id) == col(Workspace.id))
            .where(Workspace.slug == slug, Membership.user_id == user.id)
        ).first()
    if found is None:
        raise HTTPException(404, "Workspace not found")
    workspace, role = found
    context = WorkspaceContext(
        id=workspace.id,
        slug=workspace.slug,
        name=workspace.name,
        role=role,
        archived=workspace.archived_at is not None,
        user_id=user.id,
    )

    needed = _required_role(request)
    if not context.can(needed):
        raise HTTPException(403, f"This needs the {needed} role in this workspace")
    route = request.scope.get("route")
    archived_ok = getattr(getattr(route, "endpoint", None), "allows_archived", False)
    if context.archived and needed != "viewer" and not archived_ok:
        raise HTTPException(409, "This workspace is archived: it is read-only")
    return context


def scope_to_workspace(
    context: Annotated[WorkspaceContext, Depends(workspace_context)],
    session: Annotated[Session, Depends(get_session)],
) -> WorkspaceContext:
    """Router-level dependency: the request's session only sees this workspace.

    The handlers ask for `get_session` too and receive this very session (FastAPI
    resolves a dependency once per request), so none of them has to filter.
    """
    scope_session(session, context.id, context.user_id)
    return context


def can_create_workspace(user: CurrentUser) -> bool:
    return config.WORKSPACE_CREATION != "admins" or user.is_instance_admin


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:40].strip("-")
    return slug or "workspace"


def free_slug(db: Session, name: str) -> str:
    base = slugify(name)
    slug, n = base, 1
    while db.exec(select(Workspace.id).where(Workspace.slug == slug)).first():
        n += 1
        slug = f"{base}-{n}"
    return slug


def create_workspace(db: Session, name: str, owner_id: int) -> Workspace:
    workspace = Workspace(
        slug=free_slug(db, name), name=name.strip(), created_by=owner_id
    )
    db.add(workspace)
    db.flush()
    db.add(Membership(workspace_id=workspace.id, user_id=owner_id, role="owner"))
    db.commit()
    db.refresh(workspace)
    return workspace


def _owners(db: Session, workspace_id: int) -> list[Membership]:
    return list(
        db.exec(
            select(Membership).where(
                Membership.workspace_id == workspace_id, Membership.role == "owner"
            )
        ).all()
    )


def set_member(db: Session, workspace: Workspace, user: User, role: str) -> None:
    """Add a user to a workspace, or change their role."""
    if role not in ROLES:
        raise MembershipError(f"Unknown role {role!r}: use one of {', '.join(ROLES)}")
    membership = db.get(Membership, (workspace.id, user.id))
    if membership is None:
        membership = Membership(workspace_id=workspace.id, user_id=user.id, role=role)
    elif membership.role == "owner" and role != "owner":
        if len(_owners(db, workspace.id)) == 1:
            raise MembershipError("A workspace needs at least one owner")
    membership.role = role
    db.add(membership)
    db.commit()


def remove_member(db: Session, workspace: Workspace, user: User) -> None:
    membership = db.get(Membership, (workspace.id, user.id))
    if membership is None:
        raise MembershipError("This user is not a member of the workspace")
    if membership.role == "owner" and len(_owners(db, workspace.id)) == 1:
        raise MembershipError("A workspace needs at least one owner")
    db.delete(membership)
    db.commit()


def claim_default_workspace(db: Session, user: User) -> None:
    """The first instance admin to sign in owns the workspace the old data moved to.

    That workspace starts without members, so nobody could otherwise reach it.
    """
    if not is_instance_admin(user.email):
        return
    workspace = db.exec(select(Workspace).where(Workspace.slug == DEFAULT_SLUG)).first()
    if workspace is None or _owners(db, workspace.id):
        return
    set_member(db, workspace, user, "owner")
    logger.info("User %s now owns the %r workspace", user.id, DEFAULT_SLUG)
