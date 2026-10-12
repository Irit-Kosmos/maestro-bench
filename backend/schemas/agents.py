"""
Request and response models for the agents API
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

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

    @classmethod
    def from_agent(cls, agent, tags: Sequence[Tag] = ()) -> AgentResponse:
        return cls(
            id=int(agent.id) if agent.id is not None else 0,
            name=agent.name,
            description=agent.description,
            kind=agent.kind,
            default_prompt_version_id=agent.default_prompt_version_id,
            default_model_id=agent.default_model_id,
            created_at=agent.created_at,
            tags=[TagResponse.model_validate(t) for t in tags],
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
