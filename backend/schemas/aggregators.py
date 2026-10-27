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
Request and response models for aggregators API
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from schemas.agents import FormulaOutput


class FormulaCheckRequest(BaseModel):
    formulas: list[FormulaOutput]


class FormulaCheckResponse(BaseModel):
    # One message per formula, None when it is valid
    errors: list[str | None]
    # Whether each error is about the output's name rather than its formula
    name_invalid: list[bool]
    # Variables to map, in order of first appearance
    variables: list[str]


class AggregatorPreviewRequest(BaseModel):
    formulas: list[FormulaOutput]
    input_mappings: list[dict] = []
    # Prompt version each source step uses in the experiment, by step key
    prompt_versions: dict[str, int | None] = {}


class AggregatorPreviewRow(BaseModel):
    row_index: int | None
    inputs: dict[str, Any] = {}
    output: dict[str, Any] | None = None
    error: str | None = None


class AggregatorPreviewResponse(BaseModel):
    # Execution the rows come from; None when no execution has every source agent
    execution_id: int | None = None
    experiment_name: str | None = None
    # False when no execution ran the agents with the experiment's prompt
    # versions, and the rows come from other versions
    versions_match: bool = True
    rows: list[AggregatorPreviewRow] = []


class AgentOutputPaths(BaseModel):
    agent_id: int
    # Dotted paths to scalar values seen in the agent's recent outputs
    paths: list[str]
    # Dotted paths to lists of values (score distributions), for mean(), max()…
    list_paths: list[str] = []
