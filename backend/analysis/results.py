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
Reading results files, whatever version of maestro-bench wrote them.

Current files (2.x) list rows under "rows", each with its agents' outputs
under "agents". Files written before 2.0 list them under "results", with the
agents under "maestro_response.results"; they are converted to the current
shape so the rest of the analysis only knows one format.
"""


def result_rows(data: dict) -> list[dict]:
    """Rows of a results file, in the current (2.x) shape."""
    if "rows" in data:
        return data["rows"] or []
    return [_legacy_row(row) for row in data.get("results") or []]


def row_count(data: dict) -> int:
    """Number of dataset rows an execution processed."""
    total = (data.get("summary") or {}).get("total_rows")
    if isinstance(total, int):
        return total
    return len(result_rows(data))


def _legacy_row(row: dict) -> dict:
    response = row.get("maestro_response") or {}
    agents = [
        {
            "name": agent.get("agent_name"),
            "output": agent.get("result"),
            "error": agent.get("error"),
        }
        for agent in response.get("results") or []
    ]
    errors = response.get("errors") or []
    return {
        "row_index": row.get("row_index"),
        "input_data": row.get("input_data") or {},
        "agents": agents,
        # Rows that failed before reaching the pipeline have no response at all
        "error": row.get("error") or (errors[0] if errors else None),
    }
