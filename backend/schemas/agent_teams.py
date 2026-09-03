"""
Request and response models for agent teams API
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    default_prompt_version_id: int | None
    default_model_id: int | None
    team_id: int
    created_at: datetime


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
    default_prompt_version_id: int | None = None
    default_model_id: int | None = None
    team_id: int


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    default_prompt_version_id: int | None = None
    default_model_id: int | None = None
    team_id: int | None = None


# Forward reference resolution
AgentTeamWithAgents.model_rebuild()
AgentResponse.model_rebuild()
