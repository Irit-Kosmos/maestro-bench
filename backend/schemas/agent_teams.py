"""
Request and response models for agent teams API
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
    team_id: int
    created_at: datetime
    # Read by the agents list; left empty where an agent only gives context (inside a team)
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
            team_id=agent.team_id,
            created_at=agent.created_at,
            tags=[TagResponse.model_validate(t) for t in tags],
        )


class AgentTeamCreate(BaseModel):
    name: str
    description: str | None = None


class AgentTeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class AgentTeamWithAgents(BaseModel):
    """Agent team response with nested agents"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
    agents: list[AgentResponse] = []


class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    kind: AgentKind = "llm"
    default_prompt_version_id: int | None = None
    default_model_id: int | None = None
    team_id: int
    tag_ids: list[int] = []


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    default_prompt_version_id: int | None = None
    default_model_id: int | None = None
    team_id: int | None = None
    # Left out: the tags stay as they are. Sent: they become exactly these.
    tag_ids: list[int] | None = None


# Forward reference resolution
AgentTeamWithAgents.model_rebuild()
AgentResponse.model_rebuild()
