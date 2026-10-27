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

"""What the lists of experiments and batches say about an experiment's executions."""

from collections.abc import Sequence

from tables import ExperimentExecution


def duration_seconds(execution: ExperimentExecution) -> float | None:
    """How long an execution took, or None while it is still running."""
    if execution.completed_at is None:
        return None
    return (execution.completed_at - execution.started_at).total_seconds()


def latest_figures(executions: Sequence[ExperimentExecution]) -> dict:
    """Execution count of an experiment, and the figures of its latest execution.

    The latest one is the one the experiment currently stands for; earlier ones
    are only counted, and their statuses listed. `executions` are ordered from the
    newest to the oldest.
    """
    latest = executions[0] if executions else None
    return {
        "execution_count": len(executions),
        "execution_statuses": [execution.status for execution in executions],
        "duration_seconds": duration_seconds(latest) if latest else None,
        "rows_failed": latest.rows_failed if latest else None,
        "total_tokens": latest.total_tokens if latest else None,
        "total_cost_usd": latest.total_cost_usd if latest else None,
    }
