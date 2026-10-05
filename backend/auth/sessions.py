"""Server-side sessions: the cookie holds a random token, the database its hash."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, delete, select

import config
from tables import AuthSession, User

# Sliding the expiry on every request would write on every request
SLIDE_AFTER = timedelta(minutes=5)


def utcnow() -> datetime:
    """Naive UTC, like the datetimes read back from the database."""
    return datetime.now(UTC).replace(tzinfo=None)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user_id: int) -> str:
    """Open a session for a user and return the token to put in the cookie."""
    now = utcnow()
    token = secrets.token_urlsafe(32)
    absolute = now + timedelta(days=config.SESSION_MAX_DAYS)
    db.add(
        AuthSession(
            id=hash_token(token),
            user_id=user_id,
            created_at=now,
            last_seen_at=now,
            expires_at=min(now + timedelta(days=config.SESSION_IDLE_DAYS), absolute),
            absolute_expires_at=absolute,
        )
    )
    db.exec(delete(AuthSession).where(col(AuthSession.absolute_expires_at) < now))
    db.commit()
    return token


def find_session(db: Session, token: str) -> tuple[AuthSession, User] | None:
    """The live session and its user, sliding the expiry; None when it cannot be used."""
    row = db.exec(
        select(AuthSession, User)
        .join(User, col(User.id) == col(AuthSession.user_id))
        .where(AuthSession.id == hash_token(token))
    ).first()
    if row is None:
        return None
    session, user = row
    now = utcnow()
    if (
        not user.is_active
        or now >= session.expires_at
        or now >= session.absolute_expires_at
    ):
        db.delete(session)
        db.commit()
        return None
    if now - session.last_seen_at > SLIDE_AFTER:
        session.last_seen_at = now
        session.expires_at = min(
            now + timedelta(days=config.SESSION_IDLE_DAYS), session.absolute_expires_at
        )
        db.add(session)
        db.commit()
    return session, user


def end_session(db: Session, session_id: str) -> None:
    db.exec(delete(AuthSession).where(col(AuthSession.id) == session_id))
    db.commit()


def end_user_sessions(db: Session, user_id: int) -> int:
    result = db.exec(delete(AuthSession).where(col(AuthSession.user_id) == user_id))
    db.commit()
    return result.rowcount


def csrf_token(session_id: str) -> str:
    """Bound to the session: the page learns it from `/auth/me`, never from a cookie."""
    return hmac.new(
        config.SECRET_KEY.encode(), f"csrf:{session_id}".encode(), hashlib.sha256
    ).hexdigest()
