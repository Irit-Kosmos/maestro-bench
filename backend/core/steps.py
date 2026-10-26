"""
Steps of an experiment: the same agent may run more than once in a pipeline.

A step is told apart by its *key*: the id of its agent for the first one
("12"), then "12#2", "12#3"… for the following ones. Keys are text so that the
requests and the data written before agents could repeat keep their meaning.
"""

from typing import Any


def step_key(agent_id: int, instance: int = 1) -> str:
    return str(agent_id) if instance == 1 else f"{agent_id}#{instance}"


def split_step(step: object) -> tuple[int, int]:
    """(agent id, instance number) of a step key; ValueError when it is not one."""
    agent, _, instance = str(step).partition("#")
    try:
        return int(agent), int(instance) if instance else 1
    except ValueError:
        raise ValueError(f"Invalid step '{step}'") from None


def agent_id_of(step: object) -> int:
    return split_step(step)[0]


def step_label(name: str, instance: int) -> str:
    """Name a step goes by: the agent's, then "name #2", "name #3"…"""
    return name if instance == 1 else f"{name} #{instance}"


def variable_name(label: str) -> str:
    """The label as a prompt variable: "Corrector #2" is read as {{Corrector_2_output}}."""
    return label.replace(" #", " ").replace(" ", "_")


def mapping_source(mapping: dict[str, Any]) -> str | None:
    """Step an input mapping reads, whichever way it was written.

    Mappings written before agents could repeat name an agent by id only.
    """
    step = mapping.get("sourceStep")
    if step is None:
        step = mapping.get("sourceAgentId")
    return None if step is None else str(step)
