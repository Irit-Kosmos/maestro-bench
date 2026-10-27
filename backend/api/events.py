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
API router for the live run stream (Server-Sent Events)
"""

import asyncio
from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlmodel import Session, col, select

import event_bus
from auth.workspaces import WorkspaceContext, workspace_context
from db import engine
from schemas.events import RunState
from tables import Experiment, ExperimentExecution
from workspace_scope import scope_session

router = APIRouter(tags=["events"])


def _wanted(state: RunState, experiment_id: int | None, batch_id: int | None) -> bool:
    return (experiment_id is None or state.experiment_id == experiment_id) and (
        batch_id is None or state.batch_id == batch_id
    )


def _running_states(session: Session) -> list[RunState]:
    rows = session.exec(
        select(ExperimentExecution, Experiment.batch_id)
        .join(
            Experiment,
            col(Experiment.id) == col(ExperimentExecution.experiment_id),
        )
        .where(ExperimentExecution.status == "running")
    ).all()
    return [
        RunState.from_execution(execution, batch_id) for execution, batch_id in rows
    ]


def _snapshot(workspace_id: int) -> list[RunState]:
    with Session(engine) as session:
        scope_session(session, workspace_id)
        return _running_states(session)


@router.get("/events", response_class=EventSourceResponse)
async def stream_events(
    context: Annotated[WorkspaceContext, Depends(workspace_context)],
    experiment_id: int | None = None,
    batch_id: int | None = None,
) -> AsyncIterable[ServerSentEvent]:
    """
    State of the running executions of the workspace, then every change to them
    as it happens. Other workspaces' runs are never sent.

    The stream is subscribed to before the snapshot is read, so no change falls
    between the two.
    """
    with event_bus.subscribe() as queue:
        snapshot = await asyncio.to_thread(_snapshot, context.id)
        for state in snapshot:
            if _wanted(state, experiment_id, batch_id):
                yield ServerSentEvent(data=state, event="snapshot")

        while True:
            event = await queue.get()
            if event.workspace_id == context.id and _wanted(
                event.state, experiment_id, batch_id
            ):
                yield ServerSentEvent(data=event.state, event=event.name)
