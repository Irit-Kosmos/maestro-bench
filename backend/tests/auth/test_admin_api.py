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

"""What instance administrators can see: only them, only what admin/fields.py declares."""

import os
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlmodel import Session, select

import config
import workspace_files
from admin import fields, queries
from api import admin as admin_api
from tables import (
    AgentExecutionSnapshot,
    Dataset,
    Experiment,
    ExperimentExecution,
    Note,
    Prompt,
    Workspace,
)
from tests.auth.people import add_member
from tests.conftest import scoped

SECRET = "zebra-protocol-7731"

ADMIN_READS = ["/admin/accounts", "/admin/workspaces", "/admin/health"]


@pytest.fixture
def admin(alice, monkeypatch):
    monkeypatch.setattr(config, "INSTANCE_ADMINS", [alice.email])
    return alice


def _workspace_id(engine, slug: str) -> int:
    with Session(engine) as db:
        return db.exec(select(Workspace.id).where(Workspace.slug == slug)).one()


def _execution(engine, workspace_id, started_at, steps, status="completed", **fields_):
    """An execution whose steps used `(key_source, tokens, cost)` each."""
    with scoped(engine, workspace_id) as s:
        dataset = Dataset(name=f"{SECRET} dataset", file_path="d.csv")
        s.add(dataset)
        s.flush()
        experiment = Experiment(name=f"{SECRET} experiment", dataset_id=dataset.id)
        s.add(experiment)
        s.flush()
        s.add(Note(kind="experiment", item_id=experiment.id, body=f"{SECRET} note"))
        s.add(Prompt(name=f"{SECRET} prompt"))
        execution = ExperimentExecution(
            experiment_id=experiment.id,
            dataset_snapshot="{}",
            started_at=started_at,
            status=status,
            **fields_,
        )
        s.add(execution)
        s.flush()
        for order, (source, tokens, cost) in enumerate(steps):
            s.add(
                AgentExecutionSnapshot(
                    execution_id=execution.id,
                    agent_name_snapshot=f"{SECRET} agent",
                    model_name_snapshot=f"{SECRET}-model",
                    model_provider_snapshot="openai",
                    prompt_name_snapshot=f"{SECRET} prompt",
                    prompt_version_snapshot="1",
                    final_system_prompt=f"{SECRET} system",
                    execution_order=order,
                    total_tokens=tokens,
                    total_cost_usd=cost,
                    key_source=source,
                )
            )
        s.commit()


def _keys(value):
    """Every key of a JSON response, nested under its field like fields.declared_keys."""
    if isinstance(value, list):
        merged: dict = {}
        for item in value:
            for key, child in _keys(item).items():
                merged.setdefault(key, {}).update(child)
        return merged
    if isinstance(value, dict):
        return {key: _keys(child) for key, child in value.items()}
    return {}


def _model_keys(model: type[BaseModel]) -> dict:
    keys = {}
    for name, info in model.model_fields.items():
        inner = getattr(info.annotation, "__args__", (info.annotation,))[0]
        keys[name] = (
            _model_keys(inner)
            if isinstance(inner, type) and issubclass(inner, BaseModel)
            else {}
        )
    return keys


# ---------------------------------------------------------------------------
# Who
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("url", ADMIN_READS)
def test_only_instance_admins_get_in(url, admin, bob):
    assert bob.get(url).status_code == 403
    assert admin.get(url).status_code == 200


@pytest.mark.parametrize("url", [*ADMIN_READS, "/admin/visibility"])
def test_nobody_signed_out_gets_in(url, app):
    assert TestClient(app).get(url).status_code == 401


def test_everyone_can_read_what_admins_see(bob):
    body = bob.get("/admin/visibility").json()

    assert [s["key"] for s in body["sections"]] == ["accounts", "workspaces", "health"]
    assert body["never_shown"]
    assert "not logged" in body["administration_only"]


# ---------------------------------------------------------------------------
# What: only the declared fields
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "section, model",
    [
        (fields.ACCOUNTS, admin_api.AccountOut),
        (fields.WORKSPACES, admin_api.WorkspaceOut),
        (fields.HEALTH, admin_api.HealthOut),
    ],
)
def test_the_response_models_are_the_declared_fields(section, model):
    assert _model_keys(model) == fields.declared_keys(section.fields)


def test_every_admin_endpoint_is_declared():
    declared = {f"/admin/{s.key}" for s in fields.SECTIONS} | {"/admin/visibility"}
    routes = {route.path for route in admin_api.router.routes}
    assert routes == declared


def test_responses_hold_the_declared_fields_and_nothing_else(admin, bob, engine):
    slug = admin.create_workspace("Lab")
    add_member(engine, slug, bob, "editor")
    now = datetime.now(UTC)
    _execution(engine, _workspace_id(engine, slug), now, [("instance", 10, 0.1)])

    for section in fields.SECTIONS:
        body = admin.get(f"/admin/{section.key}").json()
        assert _keys(body) == fields.declared_keys(section.fields), section.key


def test_no_content_and_no_names_of_what_workspaces_hold(admin, bob, engine):
    slug = bob.create_workspace("Bob's lab")
    _execution(
        engine,
        _workspace_id(engine, slug),
        datetime.now(UTC),
        [("instance", 10, 0.1), ("workspace", 5, 0.05)],
        status="failed",
    )

    for url in ADMIN_READS:
        text = admin.get(url).text
        assert SECRET not in text, url
        assert "Bob" not in text.replace("Bob's lab", ""), url  # no display name


# ---------------------------------------------------------------------------
# The numbers
# ---------------------------------------------------------------------------


def test_accounts(admin, bob, engine):
    slug = admin.create_workspace("Lab")
    admin.create_workspace("Other")
    add_member(engine, slug, bob, "viewer")

    rows = {row["email"]: row for row in admin.get("/admin/accounts").json()}

    assert rows[admin.email]["workspace_count"] == 2
    assert rows[bob.email]["workspace_count"] == 1
    assert rows[bob.email]["active"] is True
    # The day only
    assert rows[bob.email]["last_sign_in_on"] == datetime.now(UTC).date().isoformat()


def test_workspaces_count_only_what_the_instance_pays(admin, bob, engine):
    slug = bob.create_workspace("Bob's lab")
    add_member(engine, slug, admin, "viewer")
    workspace_id = _workspace_id(engine, slug)
    now = datetime.now(UTC)
    _execution(
        engine,
        workspace_id,
        now,
        [("instance", 100, 1.5), ("workspace", 999, 9.99), (None, 7, 0.07)],
    )
    _execution(engine, workspace_id, now - timedelta(days=400), [("instance", 50, 0.5)])
    folder = workspace_files.results_dir(workspace_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "r.json").write_bytes(b"x" * 1234)

    row = next(w for w in admin.get("/admin/workspaces").json() if w["slug"] == slug)

    assert row["owner_emails"] == [bob.email]
    assert row["member_count"] == 2
    assert row["archived"] is False
    assert row["last_activity_on"] == now.date().isoformat()
    assert row["disk_bytes"] == 1234
    assert len(row["usage"]) == fields.USAGE_MONTHS
    assert row["usage"][0] == {
        "month": now.strftime("%Y-%m"),
        "tokens": 100,
        "cost_usd": 1.5,
    }
    assert all(m["tokens"] == 0 for m in row["usage"][1:])


def test_health(admin, engine):
    workspace_id = _workspace_id(engine, admin.create_workspace("Lab"))
    now = datetime.now(UTC)
    _execution(engine, workspace_id, now, [], status="running")
    _execution(engine, workspace_id, now, [], status="failed", completed_at=now)
    _execution(
        engine,
        workspace_id,
        now - timedelta(days=3),
        [],
        status="failed",
        completed_at=now - timedelta(days=3),
    )

    assert admin.get("/admin/health").json() == {
        "running_executions": 1,
        "max_concurrent_executions": config.MAX_CONCURRENT_EXPERIMENTS,
        "failed_last_24h": 1,
    }


def test_the_months_go_back_across_a_new_year():
    months = queries._months(date(2026, 1, 15))
    assert [m.isoformat() for m in months][:3] == [
        "2026-01-01",
        "2025-12-01",
        "2025-11-01",
    ]


def test_admin_queries_refuse_a_scoped_session(engine):
    with scoped(engine) as s, pytest.raises(RuntimeError):
        queries.accounts(s)


def test_disk_usage_ignores_links(tmp_path, monkeypatch, data_dir):
    folder = workspace_files.datasets_dir(42)
    folder.mkdir(parents=True)
    (folder / "a.csv").write_bytes(b"abc")
    os.symlink(folder / "a.csv", folder / "b.csv")

    assert queries.disk_bytes(42) == 3
