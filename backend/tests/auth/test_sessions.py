from datetime import timedelta

from sqlmodel import select

from auth.policy import Profile
from auth.sessions import (
    create_session,
    csrf_token,
    end_session,
    end_user_sessions,
    find_session,
    hash_token,
    utcnow,
)
from auth.users import find_users, set_active, sign_in
from tables import AuthSession, Identity, User


def make_user(session, email="remi@irit.fr", subject="1", provider="gitlab"):
    return sign_in(
        session,
        Profile(provider=provider, subject=subject, display_name="Rémi", email=email),
    )


def test_a_session_is_found_by_its_token_and_only_the_hash_is_stored(session):
    user = make_user(session)
    token = create_session(session, user.id)

    found = find_session(session, token)

    assert found is not None
    assert found[1].id == user.id
    assert [s.id for s in session.exec(select(AuthSession)).all()] == [
        hash_token(token)
    ]


def test_an_unknown_token_finds_nothing(session):
    assert find_session(session, "nope") is None


def test_an_idle_session_expires(session):
    user = make_user(session)
    token = create_session(session, user.id)
    stored = session.get(AuthSession, hash_token(token))
    stored.expires_at = utcnow() - timedelta(seconds=1)
    session.add(stored)
    session.commit()

    assert find_session(session, token) is None
    assert session.exec(select(AuthSession)).all() == []


def test_activity_slides_the_expiry_but_never_past_the_absolute_limit(session):
    user = make_user(session)
    token = create_session(session, user.id)
    stored = session.get(AuthSession, hash_token(token))
    stored.last_seen_at = utcnow() - timedelta(hours=1)
    stored.absolute_expires_at = utcnow() + timedelta(days=2)
    session.add(stored)
    session.commit()

    _, _ = find_session(session, token)

    session.refresh(stored)
    assert stored.expires_at == stored.absolute_expires_at
    assert utcnow() - stored.last_seen_at < timedelta(minutes=1)


def test_a_session_past_the_absolute_limit_is_refused(session):
    user = make_user(session)
    token = create_session(session, user.id)
    stored = session.get(AuthSession, hash_token(token))
    stored.absolute_expires_at = utcnow() - timedelta(seconds=1)
    session.add(stored)
    session.commit()

    assert find_session(session, token) is None


def test_deactivating_a_user_ends_their_sessions(session):
    user = make_user(session)
    other = make_user(session, email="b@irit.fr", subject="2")
    token = create_session(session, user.id)
    create_session(session, user.id)
    other_token = create_session(session, other.id)

    assert set_active(session, user, False) == 2

    assert find_session(session, token) is None
    assert find_session(session, other_token) is not None


def test_a_deactivated_user_cannot_use_a_session_that_survived(session):
    user = make_user(session)
    token = create_session(session, user.id)
    user.is_active = False
    session.add(user)
    session.commit()

    assert find_session(session, token) is None


def test_logging_out_removes_only_that_session(session):
    user = make_user(session)
    first = create_session(session, user.id)
    second = create_session(session, user.id)

    end_session(session, hash_token(first))

    assert find_session(session, first) is None
    assert find_session(session, second) is not None
    assert end_user_sessions(session, user.id) == 1


def test_creating_a_session_sweeps_the_dead_ones(session):
    user = make_user(session)
    old = create_session(session, user.id)
    stored = session.get(AuthSession, hash_token(old))
    stored.absolute_expires_at = utcnow() - timedelta(days=1)
    session.add(stored)
    session.commit()

    create_session(session, user.id)

    assert len(session.exec(select(AuthSession)).all()) == 1


def test_csrf_tokens_belong_to_one_session():
    assert csrf_token("a") == csrf_token("a")
    assert csrf_token("a") != csrf_token("b")


def test_signing_in_again_reuses_the_user_and_refreshes_the_profile(session):
    first = make_user(session, email="old@irit.fr")
    again = sign_in(
        session,
        Profile(
            provider="gitlab", subject="1", display_name="Rémi S.", email="new@irit.fr"
        ),
    )

    assert again.id == first.id
    assert again.email == "new@irit.fr"
    assert again.display_name == "Rémi S."
    assert again.last_login_at is not None
    assert len(session.exec(select(User)).all()) == 1


def test_accounts_are_not_merged_by_email(session):
    first = make_user(session, provider="gitlab", subject="1")
    second = make_user(session, provider="github", subject="9")

    assert first.id != second.id
    assert len(session.exec(select(Identity)).all()) == 2


def test_a_deactivated_user_keeps_their_profile_when_they_try_to_sign_in(session):
    user = make_user(session, email="old@irit.fr")
    set_active(session, user, False)

    again = sign_in(
        session,
        Profile(provider="gitlab", subject="1", display_name="X", email="new@irit.fr"),
    )

    assert again.is_active is False
    assert again.email == "old@irit.fr"


def test_users_are_found_by_id_or_email_ignoring_case(session):
    user = make_user(session, email="Remi@irit.fr")

    assert [u.id for u in find_users(session, str(user.id))] == [user.id]
    assert [u.id for u in find_users(session, "remi@IRIT.fr")] == [user.id]
    assert find_users(session, "nobody@irit.fr") == []
