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
Request and response models for the agents API
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from schemas.people import PersonResponse
from schemas.tags import TagResponse
from tables import Tag

AgentKind = Literal["llm", "aggregator"]


class FormulaOutput(BaseModel):
    """One named output of an aggregator, computed by a formula."""

    name: str
    formula: str


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    kind: AgentKind = "llm"
    default_prompt_version_id: int | None
    default_model_id: int | None
    created_at: datetime
    tags: list[TagResponse] = []
    # None when nobody is known to have made it (made before authors were kept, or the account is gone)
    author: PersonResponse | None = None

    @classmethod
    def from_agent(
        cls, agent, tags: Sequence[Tag] = (), author: PersonResponse | None = None
    ) -> AgentResponse:
        return cls(
            id=int(agent.id) if agent.id is not None else 0,
            name=agent.name,
            description=agent.description,
            kind=agent.kind,
            default_prompt_version_id=agent.default_prompt_version_id,
            default_model_id=agent.default_model_id,
            created_at=agent.created_at,
            tags=[TagResponse.model_validate(t) for t in tags],
            author=author,
        )


class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    kind: AgentKind = "llm"
    default_prompt_version_id: int | None = None
    default_model_id: int | None = None
    tag_ids: list[int] = []


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    default_prompt_version_id: int | None = None
    default_model_id: int | None = None
    # Left out: the tags stay as they are. Sent: they become exactly these.
    tag_ids: list[int] | None = None
