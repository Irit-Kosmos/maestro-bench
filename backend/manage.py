"""
Administration commands, run inside the backend container:

    docker compose exec backend uv run python manage.py users list
    docker compose exec backend uv run python manage.py users deactivate <email|id>
    docker compose exec backend uv run python manage.py users activate <email|id>
    docker compose exec backend uv run python manage.py users logout <email|id>
"""

import argparse
import sys

from sqlmodel import Session, select

import auth.policy
from auth.sessions import end_user_sessions
from auth.users import find_users, set_active
from db import engine
from tables import Identity, User


def _one_user(db: Session, ref: str) -> User:
    users = find_users(db, ref)
    if not users:
        sys.exit(f"No user matches {ref!r}")
    if len(users) > 1:
        ids = ", ".join(str(user.id) for user in users)
        sys.exit(f"{ref!r} matches several users (ids {ids}): use an id")
    return users[0]


def list_users() -> None:
    with Session(engine) as db:
        identities = db.exec(select(Identity)).all()
        providers: dict[int, list[str]] = {}
        for identity in identities:
            providers.setdefault(identity.user_id, []).append(identity.provider)
        print(f"{'ID':>4}  {'STATE':<8} {'ADMIN':<6} {'EMAIL':<36} NAME (providers)")
        for user in db.exec(select(User).order_by(User.id)).all():
            state = "active" if user.is_active else "disabled"
            admin = "admin" if auth.policy.is_instance_admin(user.email) else ""
            via = ", ".join(providers.get(user.id, []))
            print(
                f"{user.id:>4}  {state:<8} {admin:<6} {user.email or '-':<36} "
                f"{user.display_name} ({via})"
            )


def switch(ref: str, active: bool) -> None:
    with Session(engine) as db:
        user = _one_user(db, ref)
        closed = set_active(db, user, active)
        if active:
            print(
                f"User {user.id} ({user.email or user.display_name}) can sign in again"
            )
        else:
            print(
                f"User {user.id} ({user.email or user.display_name}) is disabled; "
                f"{closed} session(s) closed"
            )


def logout(ref: str) -> None:
    with Session(engine) as db:
        user = _one_user(db, ref)
        print(f"{end_user_sessions(db, user.id)} session(s) closed for user {user.id}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="manage.py")
    groups = parser.add_subparsers(dest="group", required=True)
    users = groups.add_parser("users", help="manage the people who can sign in")
    actions = users.add_subparsers(dest="action", required=True)
    actions.add_parser("list", help="list every user")
    for name, help_text in (
        ("deactivate", "block a user and close their sessions"),
        ("activate", "let a blocked user sign in again"),
        ("logout", "close every session of a user"),
    ):
        action = actions.add_parser(name, help=help_text)
        action.add_argument("user", help="email or id")

    args = parser.parse_args()
    match args.action:
        case "list":
            list_users()
        case "deactivate":
            switch(args.user, False)
        case "activate":
            switch(args.user, True)
        case "logout":
            logout(args.user)


if __name__ == "__main__":
    main()
