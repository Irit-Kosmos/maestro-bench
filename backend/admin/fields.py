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
Every piece of information an instance administrator can see, each with the task it serves.

This list is the single source of truth. The admin API returns these fields and no
other (a test fails otherwise), and the "What administrators can see" page, shown to
every signed-in user, is generated from it. To show administrators anything more, add
it here first, with the task that needs it, so everyone can see the change.

Three rules:
- collect and show as little as possible: a field is only here if an admin task needs it;
- be transparent: every user can read this list, in the app and in the README;
- administration only: aggregates and dates, never what people work on.
"""

from dataclasses import dataclass, field

# How many months of instance-paid usage a workspace shows, the current one included
USAGE_MONTHS = 3


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    # The admin task that needs it
    purpose: str
    # How the page shows it: text, id, email-list, bool, day, count, bytes, usd, month, table
    kind: str = "text"
    # The fields of each row, for a field that is a small table
    fields: tuple["Field", ...] = ()


@dataclass(frozen=True)
class Section:
    key: str  # also the endpoint: GET /admin/<key>
    title: str
    task: str
    fields: tuple[Field, ...] = field(default_factory=tuple)


ACCOUNTS = Section(
    key="accounts",
    title="Accounts",
    task="Who can sign in",
    fields=(
        Field(
            "id", "Account number", "Tells apart two accounts with the same email", "id"
        ),
        Field("email", "Email", "Finds the account, reaches its owner", "text"),
        Field("active", "Active", "Whether it can sign in", "bool"),
        Field(
            "last_sign_in_on", "Last sign-in", "Spots unused accounts (day only)", "day"
        ),
        Field("workspace_count", "Workspaces", "How many, not which", "count"),
    ),
)

WORKSPACES = Section(
    key="workspaces",
    title="Workspaces",
    task="Capacity, cost, contacts",
    fields=(
        Field("slug", "Identifier", "Names it in admin commands", "id"),
        Field("name", "Name", "Tells workspaces apart", "text"),
        Field("owner_emails", "Owners", "Who to contact", "email-list"),
        Field("member_count", "Members", "How many, not who", "count"),
        Field("created_on", "Created", "Age (day only)", "day"),
        Field("archived", "Archived", "Whether it is read-only", "bool"),
        Field("last_activity_on", "Last activity", "Day of the last execution", "day"),
        Field("disk_bytes", "Disk", "Size of datasets and results", "bytes"),
        Field(
            "usage",
            "Monthly cost",
            f"Instance's API keys only, last {USAGE_MONTHS} months",
            "table",
            fields=(
                Field("month", "Month", "Calendar month (UTC)", "month"),
                Field("tokens", "Tokens", "On the instance's keys", "count"),
                Field("cost_usd", "Cost", "On the instance's keys, estimated", "usd"),
                Field(
                    "unknown_source_tokens",
                    "Tokens, key unknown",
                    "Older runs that did not record whose key paid",
                    "count",
                ),
                Field(
                    "unknown_source_cost_usd",
                    "Cost, key unknown",
                    "Same, estimated cost",
                    "usd",
                ),
            ),
        ),
    ),
)

HEALTH = Section(
    key="health",
    title="Instance health",
    task="Load and outages",
    fields=(
        Field(
            "running_executions",
            "Running executions",
            "All workspaces together",
            "count",
        ),
        Field(
            "max_concurrent_executions",
            "Allowed at once",
            "The instance's limit",
            "count",
        ),
        Field(
            "failed_last_24h",
            "Failed, last 24 hours",
            "A count, not which ones",
            "count",
        ),
    ),
)

SECTIONS: tuple[Section, ...] = (ACCOUNTS, WORKSPACES, HEALTH)

# What administrators never see through the app, whatever the task
NEVER_SHOWN: tuple[str, ...] = (
    "Names or content of anything in a workspace",
    "Outputs, results, notes and shared links",
    "Display names, avatars and API keys",
    "Members other than owners, and roles",
    "Who did what, and when",
    "Spend on a workspace's own API keys",
)

ADMINISTRATION_ONLY = "Used only to run the instance. Viewing it is not logged."


def declared_keys(fields: tuple[Field, ...]) -> dict[str, dict]:
    """The declared keys, with those of a field's rows nested under it."""
    return {f.key: declared_keys(f.fields) for f in fields}


def _field_out(f: Field) -> dict:
    return {
        "key": f.key,
        "label": f.label,
        "purpose": f.purpose,
        "kind": f.kind,
        "fields": [_field_out(child) for child in f.fields],
    }


def disclosure() -> dict:
    """The whole list, as the transparency page shows it to every user."""
    return {
        "sections": [
            {
                "key": s.key,
                "title": s.title,
                "task": s.task,
                "fields": [_field_out(f) for f in s.fields],
            }
            for s in SECTIONS
        ],
        "never_shown": list(NEVER_SHOWN),
        "administration_only": ADMINISTRATION_ONLY,
    }
