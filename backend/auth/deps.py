"""FastAPI dependency that guards the API: a live session, plus CSRF on writes."""

import hmac
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.engine import Engine
from sqlmodel import Session

import config
import db
from auth.policy import is_instance_admin
from auth.sessions import csrf_token, find_session

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "X-CSRF-Token"


@dataclass(frozen=True)
class CurrentUser:
    id: int
    display_name: str
    email: str | None
    avatar_url: str | None
    is_instance_admin: bool
    session_id: str


def get_engine() -> Engine:
    """The engine the session lookup uses; a dependency so tests can swap it."""
    return db.engine


def allowed_origins() -> set[str]:
    return {*config.CORS_ORIGINS, config.FRONTEND_URL} - {""}


def _check_csrf(request: Request, session_id: str) -> None:
    # Browsers always say where a cross-site write comes from
    origin = request.headers.get("origin")
    if origin is not None and origin not in allowed_origins():
        raise HTTPException(403, "Origin not allowed")
    sent = request.headers.get(CSRF_HEADER, "")
    if not hmac.compare_digest(sent, csrf_token(session_id)):
        raise HTTPException(403, "Missing or invalid CSRF token")


def require_user(
    request: Request, engine: Annotated[Engine, Depends(get_engine)]
) -> CurrentUser:
    token = request.cookies.get(config.SESSION_COOKIE_NAME)
    found = None
    if token:
        # Own short session: the stream endpoint must not hold a connection open
        with Session(engine) as session:
            found = find_session(session, token)
            if found:
                auth_session, user = found
                current = CurrentUser(
                    id=user.id,
                    display_name=user.display_name,
                    email=user.email,
                    avatar_url=user.avatar_url,
                    is_instance_admin=is_instance_admin(user.email),
                    session_id=auth_session.id,
                )
    if not found:
        raise HTTPException(401, "Not authenticated")
    if request.method not in SAFE_METHODS:
        _check_csrf(request, current.session_id)
    return current
