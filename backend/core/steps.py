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
Steps of an experiment: the same agent may run more than once in a pipeline.

A step is told apart by its *key*: the id of its agent for the first one
("12"), then "12#2", "12#3"… for the following ones. Keys are text so that the
requests and the data written before agents could repeat keep their meaning.
"""

from typing import Any


def step_key(agent_id: int, instance: int = 1) -> str:
    return str(agent_id) if instance == 1 else f"{agent_id}#{instance}"


def split_step(step: object) -> tuple[int, int]:
    """(agent id, instance number) of a step key; ValueError when it is not one.

    Only the form `step_key` writes is one: "012" or "12#1" would name the step
    "12" under a key nothing else looks it up by.
    """
    agent, _, instance = str(step).partition("#")
    try:
        parsed = int(agent), int(instance) if instance else 1
    except ValueError:
        raise ValueError(f"Invalid step '{step}'") from None
    if parsed[1] < 1 or step_key(*parsed) != str(step):
        raise ValueError(f"Invalid step '{step}'")
    return parsed


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
