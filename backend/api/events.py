"""
API router for the live run stream (Server-Sent Events)
"""

from collections.abc import AsyncIterable

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlmodel import Session, col, select

import event_bus
from db import engine
from schemas.events import RunState
from tables import Experiment, ExperimentExecution

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


@router.get("/events", response_class=EventSourceResponse)
async def stream_events(
    experiment_id: int | None = None, batch_id: int | None = None
) -> AsyncIterable[ServerSentEvent]:
    """
    State of the running executions, then every change to them as it happens.

    The stream is subscribed to before the snapshot is read, so no change falls
    between the two.
    """
    with event_bus.subscribe() as queue:
        with Session(engine) as session:
            snapshot = _running_states(session)
        for state in snapshot:
            if _wanted(state, experiment_id, batch_id):
                yield ServerSentEvent(data=state, event="snapshot")

        while True:
            event = await queue.get()
            if _wanted(event.state, experiment_id, batch_id):
                yield ServerSentEvent(data=event.state, event=event.name)
