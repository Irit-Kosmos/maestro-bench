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
    # Only the members of this workspace may be told; not part of the payload
    workspace_id: int
