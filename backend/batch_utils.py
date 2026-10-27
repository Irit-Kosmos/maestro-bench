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
Pure helpers for batches: expanding variations into grid points, checking that
a prompt can replace another, and labelling the resulting experiments.

A *variation* is one axis of the grid: ``{"step_key", "agent_id", "field",
"values"}``, where the step is one run of an agent in the experiment (see
core.steps). A batch's experiments are the cartesian product of its axes; each
experiment sits at one *point* ``{step_key: {field: value}}``.
"""

import itertools
import json
import math
from typing import Any

from core.steps import agent_id_of

# Fields of an agent's experiment configuration that a batch may vary
VARIABLE_FIELDS = ("model_id", "prompt_version_id", "temperature")

# Safety net against a typo turning into hundreds of paid runs
MAX_BATCH_EXPERIMENTS = 50

Point = dict[str, dict[str, Any]]


class VariationError(ValueError):
    """The requested variations cannot be turned into a batch."""


def variation_step(variation: dict) -> str:
    """Step an axis varies. Axes stored before agents could repeat name an agent only."""
    return str(variation.get("step_key") or variation["agent_id"])


def normalize_variations(variations: list[dict]) -> list[dict]:
    """Validate the axes and drop duplicate values (keeping the order)."""
    if not variations:
        raise VariationError("A batch needs at least one variation")

    seen: set[tuple[str, str]] = set()
    normalized = []
    for variation in variations:
        step, field = variation_step(variation), variation["field"]
        try:
            agent_id_of(step)
        except ValueError as e:
            raise VariationError(str(e)) from e
        if field not in VARIABLE_FIELDS:
            raise VariationError(f"Field '{field}' cannot be varied")
        if (step, field) in seen:
            raise VariationError(f"Step {step} varies '{field}' more than once")
        seen.add((step, field))

        values = list(dict.fromkeys(variation["values"]))
        if not values:
            raise VariationError(f"Variation of '{field}' has no values")
        if field == "temperature":
            # None is the model's own default temperature
            if not all(
                v is None or (math.isfinite(v) and v >= 0) for v in values
            ):
                raise VariationError("Temperature values must be numbers >= 0")
        elif None in values:
            raise VariationError(f"Variation of '{field}' needs a value")
        normalized.append(
            {
                "step_key": step,
                "agent_id": agent_id_of(step),
                "field": field,
                "values": values,
            }
        )
    return normalized


def count_points(variations: list[dict]) -> int:
    return math.prod(len(v["values"]) for v in variations)


def is_base_point(point: Point, base_values: dict[tuple[str, str], Any]) -> bool:
    """Whether the point takes, on every axis, the value of the base configuration."""
    return all(
        fields[field] == base_values[(step, field)]
        for step, fields in point.items()
        for field in fields
    )


def expand_variations(variations: list[dict]) -> list[Point]:
    """Cartesian product of the axes, first axis varying slowest."""
    points: list[Point] = []
    for combo in itertools.product(*(v["values"] for v in variations)):
        point: Point = {}
        for variation, value in zip(variations, combo, strict=True):
            point.setdefault(variation_step(variation), {})[variation["field"]] = value
        points.append(point)
    return points


def serialize_point(point: Point) -> str:
    return json.dumps(point)


def parse_point(raw: str | None) -> Point:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return {str(step): fields for step, fields in data.items()}


def prompt_variable_names(raw: str | None) -> set[str]:
    """Variable names of a prompt version ("variables" is a JSON list or object)."""
    if not raw:
        return set()
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return set()
    if isinstance(parsed, list):
        return {str(name) for name in parsed}
    if isinstance(parsed, dict):
        return set(parsed)
    return set()


def mapped_variable_names(input_mappings: list[dict] | None) -> set[str] | None:
    """Variables an agent's mappings feed, or None when it has no mappings.

    Without mappings the orchestrator hands the agent the whole row plus every
    previous output, so any prompt can run.
    """
    if not input_mappings:
        return None
    return {
        m["variable"] for m in input_mappings if m.get("variable") and m.get("source")
    }


def unmapped_variables(
    prompt_variables: set[str], input_mappings: list[dict] | None
) -> set[str]:
    """Variables of a prompt that the agent's mappings do not provide."""
    mapped = mapped_variable_names(input_mappings)
    return set() if mapped is None else prompt_variables - mapped


def format_temperature(value: float | None) -> str:
    return "default T" if value is None else f"T={value:g}"


def variant_label(parts: list[str]) -> str:
    return " · ".join(parts)


def batch_status(statuses: list[str]) -> str:
    """Overall status of a batch from the statuses of its experiments."""
    if not statuses:
        return "pending"
    if any(s == "running" for s in statuses):
        return "running"
    if any(s in ("pending", "queued") for s in statuses):
        return "pending"
    if all(s == "completed" for s in statuses):
        return "completed"
    if any(s == "completed" for s in statuses):
        return "partial"
    if any(s == "failed" for s in statuses):
        return "failed"
    return "cancelled"
