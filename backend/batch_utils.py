"""
Pure helpers for batches: expanding variations into grid points, checking that
a prompt can replace another, and labelling the resulting experiments.

A *variation* is one axis of the grid: ``{"agent_id", "field", "values"}``.
A batch's experiments are the cartesian product of its axes; each experiment
sits at one *point* ``{agent_id: {field: value}}``.
"""

import itertools
import json
import math
from typing import Any

# Fields of an agent's experiment configuration that a batch may vary
VARIABLE_FIELDS = ("model_id", "prompt_version_id", "temperature")

# Safety net against a typo turning into hundreds of paid runs
MAX_BATCH_EXPERIMENTS = 50

Point = dict[int, dict[str, Any]]


class VariationError(ValueError):
    """The requested variations cannot be turned into a batch."""


def normalize_variations(variations: list[dict]) -> list[dict]:
    """Validate the axes and drop duplicate values (keeping the order)."""
    if not variations:
        raise VariationError("A batch needs at least one variation")

    seen: set[tuple[int, str]] = set()
    normalized = []
    for variation in variations:
        agent_id, field = variation["agent_id"], variation["field"]
        if field not in VARIABLE_FIELDS:
            raise VariationError(f"Field '{field}' cannot be varied")
        if (agent_id, field) in seen:
            raise VariationError(f"Agent {agent_id} varies '{field}' more than once")
        seen.add((agent_id, field))

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
        normalized.append({"agent_id": agent_id, "field": field, "values": values})
    return normalized


def count_points(variations: list[dict]) -> int:
    return math.prod(len(v["values"]) for v in variations)


def is_base_point(point: Point, base_values: dict[tuple[int, str], Any]) -> bool:
    """Whether the point takes, on every axis, the value of the base configuration."""
    return all(
        fields[field] == base_values[(agent_id, field)]
        for agent_id, fields in point.items()
        for field in fields
    )


def expand_variations(variations: list[dict]) -> list[Point]:
    """Cartesian product of the axes, first axis varying slowest."""
    points: list[Point] = []
    for combo in itertools.product(*(v["values"] for v in variations)):
        point: Point = {}
        for variation, value in zip(variations, combo, strict=True):
            point.setdefault(variation["agent_id"], {})[variation["field"]] = value
        points.append(point)
    return points


def serialize_point(point: Point) -> str:
    return json.dumps({str(agent_id): fields for agent_id, fields in point.items()})


def parse_point(raw: str | None) -> Point:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return {int(agent_id): fields for agent_id, fields in data.items()}


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
    if any(s == "pending" for s in statuses):
        return "pending"
    if all(s == "completed" for s in statuses):
        return "completed"
    if any(s == "completed" for s in statuses):
        return "partial"
    if any(s == "failed" for s in statuses):
        return "failed"
    return "cancelled"
