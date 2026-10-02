"""
Payloads of the live run stream
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from tables import ExperimentExecution


class RunState(BaseModel):
    """Whole state of an execution: a client replaces what it knows with it."""

    experiment_id: int
    batch_id: int | None = None
    # None when the run failed before an execution was created
    execution_id: int | None = None
    status: str
    rows_total: int | None = None
    rows_done: int = 0
    rows_failed: int = 0

    @classmethod
    def from_execution(
        cls, execution: ExperimentExecution, batch_id: int | None
    ) -> RunState:
        return cls(
            experiment_id=execution.experiment_id,
            batch_id=batch_id,
            execution_id=execution.id,
            status=execution.status,
            rows_total=execution.rows_total,
            rows_done=execution.rows_done,
            rows_failed=execution.rows_failed,
        )


class RunEvent(BaseModel):
    """`progress` follows a row finishing, `status` an execution changing status."""

    name: Literal["progress", "status"]
    state: RunState
