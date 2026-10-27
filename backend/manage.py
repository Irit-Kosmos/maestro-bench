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
Administration commands, run inside the backend container:

    docker compose exec backend uv run python manage.py users list
    docker compose exec backend uv run python manage.py users deactivate <email|id>
    docker compose exec backend uv run python manage.py users activate <email|id>
    docker compose exec backend uv run python manage.py users logout <email|id>

    docker compose exec backend uv run python manage.py workspaces list
    docker compose exec backend uv run python manage.py workspaces members <slug>
    docker compose exec backend uv run python manage.py workspaces add-member <slug> <email|id> <viewer|editor|owner>
    docker compose exec backend uv run python manage.py workspaces remove-member <slug> <email|id>
"""

import argparse
import sys

from sqlmodel import Session, func, select

import auth.policy
from auth.sessions import end_user_sessions
from auth.users import find_users, set_active
from auth.workspaces import (
    ROLES,
    MembershipError,
    remove_member,
    role_rank,
    set_member,
)
from db import engine
from tables import Identity, Membership, User, Workspace


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


def _workspace(db: Session, slug: str) -> Workspace:
    workspace = db.exec(select(Workspace).where(Workspace.slug == slug)).first()
    if workspace is None:
        sys.exit(f"No workspace {slug!r}")
    return workspace


def list_workspaces() -> None:
    with Session(engine) as db:
        counts = dict(
            db.exec(
                select(Membership.workspace_id, func.count()).group_by(
                    Membership.workspace_id
                )
            ).all()
        )
        print(f"{'ID':>4}  {'STATE':<9} {'MEMBERS':>7}  {'SLUG':<24} NAME")
        for workspace in db.exec(select(Workspace).order_by(Workspace.id)).all():
            state = "archived" if workspace.archived_at else "active"
            print(
                f"{workspace.id:>4}  {state:<9} {counts.get(workspace.id, 0):>7}  "
                f"{workspace.slug:<24} {workspace.name}"
            )


def list_members(slug: str) -> None:
    with Session(engine) as db:
        workspace = _workspace(db, slug)
        rows = db.exec(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(Membership.workspace_id == workspace.id)
        ).all()
        print(f"{workspace.name} ({workspace.slug})")
        for membership, user in sorted(rows, key=lambda r: -role_rank(r[0].role)):
            print(
                f"  {membership.role:<7} {user.id:>4}  {user.email or '-':<36} "
                f"{user.display_name}"
            )
        if not rows:
            print("  no members")


def add_member(slug: str, ref: str, role: str) -> None:
    with Session(engine) as db:
        workspace = _workspace(db, slug)
        user = _one_user(db, ref)
        try:
            set_member(db, workspace, user, role)
        except MembershipError as error:
            sys.exit(str(error))
        print(f"{user.email or user.display_name} is now {role} of {workspace.slug}")


def drop_member(slug: str, ref: str) -> None:
    with Session(engine) as db:
        workspace = _workspace(db, slug)
        user = _one_user(db, ref)
        try:
            remove_member(db, workspace, user)
        except MembershipError as error:
            sys.exit(str(error))
        print(f"{user.email or user.display_name} left {workspace.slug}")


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

    workspaces = groups.add_parser("workspaces", help="manage workspaces and members")
    ws_actions = workspaces.add_subparsers(dest="action", required=True)
    ws_actions.add_parser("list", help="list every workspace")
    members = ws_actions.add_parser("members", help="list the members of a workspace")
    members.add_argument("slug")
    add = ws_actions.add_parser("add-member", help="add a user, or change their role")
    add.add_argument("slug")
    add.add_argument("user", help="email or id")
    add.add_argument("role", choices=ROLES)
    remove = ws_actions.add_parser(
        "remove-member", help="take a user out of a workspace"
    )
    remove.add_argument("slug")
    remove.add_argument("user", help="email or id")

    args = parser.parse_args()
    if args.group == "workspaces":
        match args.action:
            case "list":
                list_workspaces()
            case "members":
                list_members(args.slug)
            case "add-member":
                add_member(args.slug, args.user, args.role)
            case "remove-member":
                drop_member(args.slug, args.user)
        return
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
