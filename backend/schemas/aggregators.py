"""
Request and response models for aggregators API
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from schemas.agent_teams import FormulaOutput


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
    # Prompt version each source agent uses in the experiment, by agent id
    prompt_versions: dict[int, int | None] = {}


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
