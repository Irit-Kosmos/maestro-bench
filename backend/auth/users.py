"""Creating, finding and switching off users."""

from sqlmodel import Session, col, func, select

from auth.policy import Profile
from auth.sessions import end_user_sessions, utcnow
from tables import Identity, User


def sign_in(db: Session, profile: Profile) -> User:
    """The user behind a provider account, created on first sight.

    Accounts are never merged by email: a second provider means a second user
    until the person links them on purpose.
    """
    identity = db.exec(
        select(Identity).where(
            Identity.provider == profile.provider, Identity.subject == profile.subject
        )
    ).first()
    user = db.get(User, identity.user_id) if identity else None
    if user is None:
        user = User(display_name=profile.display_name)
        db.add(user)
        db.flush()
        identity = Identity(
            user_id=user.id, provider=profile.provider, subject=profile.subject
        )
    assert identity is not None and user.id is not None
    if user.is_active:
        user.display_name = profile.display_name
        user.email = profile.email
        user.avatar_url = profile.avatar_url
        user.last_login_at = utcnow()
        identity.email_at_login = profile.email
    db.add(user)
    db.add(identity)
    db.commit()
    db.refresh(user)
    return user


def find_users(db: Session, ref: str) -> list[User]:
    """Users matching a numeric id or an email (ignoring case)."""
    if ref.isdecimal():
        user = db.get(User, int(ref))
        return [user] if user else []
    return list(
        db.exec(select(User).where(func.lower(col(User.email)) == ref.lower())).all()
    )


def set_active(db: Session, user: User, active: bool) -> int:
    """Switch an account on or off; switching off ends its sessions. Returns how many."""
    user.is_active = active
    db.add(user)
    db.commit()
    return 0 if active else end_user_sessions(db, user.id)
