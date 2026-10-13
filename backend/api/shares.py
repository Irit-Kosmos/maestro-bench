"""Making and withdrawing the public links of a workspace's items.

Reading through a link is `api/shared.py`.
"""

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

import config
from auth.workspaces import allows_archived, requires
from db import SessionDep
from schemas.shares import ShareCreate, ShareKind, ShareResponse
from study_utils import NOTE_TABLES
from tables import Share
from workspace_scope import current_user_id

router = APIRouter(tags=["shares"])

# 128 bits: a link cannot be guessed
TOKEN_BYTES = 16


def _active(session: Session, kind: str, item_id: int) -> Share | None:
    return session.exec(
        select(Share).where(
            Share.kind == kind, Share.item_id == item_id, Share.revoked_at.is_(None)
        )
    ).first()


def _to_response(share: Share) -> ShareResponse:
    return ShareResponse(
        id=int(share.id),
        kind=share.kind,
        item_id=share.item_id,
        token=share.token,
        created_at=share.created_at,
    )


@router.get("/shares", response_model=ShareResponse | None)
@requires("editor")
@allows_archived
def get_share(kind: ShareKind, item_id: int, session: SessionDep):
    """The active link of an item, or null. Editors only: the token is the link."""
    share = _active(session, kind, item_id)
    return _to_response(share) if share else None


@router.post("/shares", response_model=ShareResponse, status_code=201)
@requires("editor")
def create_share(data: ShareCreate, session: SessionDep, response: Response):
    """Make the link of an item: the active one when there already is one (200)."""
    if not config.PUBLIC_SHARING_ENABLED:
        raise HTTPException(
            status_code=403, detail="Public links are turned off on this instance"
        )
    if session.get(NOTE_TABLES[data.kind], data.item_id) is None:
        raise HTTPException(
            status_code=404, detail=f"{data.kind.capitalize()} not found"
        )

    if existing := _active(session, data.kind, data.item_id):
        response.status_code = 200
        return _to_response(existing)

    share = Share(
        kind=data.kind,
        item_id=data.item_id,
        token=secrets.token_urlsafe(TOKEN_BYTES),
        created_by=current_user_id(session),
    )
    session.add(share)
    try:
        session.commit()
    except IntegrityError:
        # Someone made the link of this item at the same moment
        session.rollback()
        existing = _active(session, data.kind, data.item_id)
        if existing is None:
            raise
        response.status_code = 200
        return _to_response(existing)
    session.refresh(share)
    return _to_response(share)


@router.delete("/shares/{share_id}", status_code=204)
@requires("editor")
@allows_archived
def revoke_share(share_id: int, session: SessionDep):
    """Withdraw a link: it stops answering and says it is no longer active.

    Also in an archived workspace: stopping an exposure is never refused.
    """
    share = session.get(Share, share_id)
    if share is None:
        raise HTTPException(status_code=404, detail="Link not found")
    if share.revoked_at is None:
        share.revoked_at = datetime.now(UTC)
        share.revoked_by = current_user_id(session)
        session.add(share)
        session.commit()
