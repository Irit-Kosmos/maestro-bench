"""
Request and response models for agent teams API
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str]
    default_prompt_version_id: Optional[int]
    default_model_id: Optional[int]
    team_id: int
    created_at: datetime


class AgentTeamCreate(BaseModel):
    name: str
    description: Optional[str] = None


class AgentTeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AgentTeamWithAgents(BaseModel):
    """Agent team response with nested agents"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    agents: List[AgentResponse] = []


class AgentTeamBasic(BaseModel):
    """Basic agent team response without nested agents"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str]
    created_at: datetime


class AgentTeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    agents: List[AgentResponse] = []


class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    default_prompt_version_id: Optional[int] = None
    default_model_id: Optional[int] = None
    team_id: int


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_prompt_version_id: Optional[int] = None
    default_model_id: Optional[int] = None


class ExperimentConfigCreate(BaseModel):
    agent_team_id: int
    active: bool = True
    priority: int = 1


class ExperimentConfigResponse(BaseModel):
    id: int
    experiment_id: int
    agent_team_id: int
    active: bool
    priority: int
    created_at: datetime
    agent_team: Optional[AgentTeamResponse] = None


class ExperimentConfigUpdate(BaseModel):
    active: Optional[bool] = None
    priority: Optional[int] = None


# Forward reference resolution
AgentTeamResponse.model_rebuild()
AgentResponse.model_rebuild()
ExperimentConfigResponse.model_rebuild()
