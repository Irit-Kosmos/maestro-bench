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

"""Builders for synthetic result rows, shaped like a results file's "rows"."""

import pytest


def make_row(
    row_index: int,
    truth=None,
    output=None,
    agent: str = "Grader",
    error: str | None = None,
    truth_column: str = "score",
    dataset_row_id: int | None = None,
) -> dict:
    agents = (
        []
        if output is _NOT_REACHED
        else [{"name": agent, "output": output, "error": error}]
    )
    row = {
        "row_index": row_index,
        "input_data": {truth_column: truth},
        "agents": agents,
    }
    if dataset_row_id is not None:
        row["dataset_row_id"] = dataset_row_id
    return row


_NOT_REACHED = object()


@pytest.fixture
def not_reached():
    """Pass as `output` for an agent the pipeline never got to."""
    return _NOT_REACHED


def scored_rows(pairs: list[tuple], agent: str = "Grader") -> list[dict]:
    """Rows whose agent output is {"score": pred}, from (pred, truth) pairs."""
    return [
        make_row(i + 1, truth=truth, output={"score": pred}, agent=agent)
        for i, (pred, truth) in enumerate(pairs)
    ]
