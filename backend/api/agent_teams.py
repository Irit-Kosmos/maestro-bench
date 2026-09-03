from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from db import get_session
from schemas.agent_teams import (
    AgentResponse,
    AgentTeamCreate,
    AgentTeamUpdate,
    AgentTeamWithAgents,
)
from tables import Agent, AgentTeam

router = APIRouter(tags=["agent-teams"])


@router.get("/agent-teams", response_model=list[AgentTeamWithAgents])
def list_agent_teams(session: Annotated[Session, Depends(get_session)]):
    teams = session.exec(select(AgentTeam)).all()
    result = []
    for team in teams:
        # Fetch agents for this team
        agents = session.exec(select(Agent).where(Agent.team_id == team.id)).all()
        team_with_agents = AgentTeamWithAgents(
            id=int(team.id) if team.id is not None else 0,
            name=team.name,
            description=team.description,
            created_at=team.created_at,
            agents=[
                AgentResponse(
                    id=int(agent.id) if agent.id is not None else 0,
                    name=agent.name,
                    description=agent.description,
                    default_prompt_version_id=agent.default_prompt_version_id,
                    default_model_id=agent.default_model_id,
                    team_id=agent.team_id,
                    created_at=agent.created_at,
                )
                for agent in agents
            ],
        )
        result.append(team_with_agents)
    return result


@router.post("/agent-teams", response_model=AgentTeamWithAgents, status_code=201)
def create_agent_team(
    team_data: AgentTeamCreate,
    session: Annotated[Session, Depends(get_session)],
):
    team = AgentTeam(name=team_data.name, description=team_data.description)
    session.add(team)
    session.commit()
    session.refresh(team)

    # Return with empty agents list for new team
    return AgentTeamWithAgents(
        id=int(team.id) if team.id is not None else 0,
        name=team.name,
        description=team.description,
        created_at=team.created_at,
        agents=[],
    )


@router.get("/agent-teams/{team_id}", response_model=AgentTeamWithAgents)
def get_agent_team(team_id: int, session: Annotated[Session, Depends(get_session)]):
    team = session.get(AgentTeam, team_id)
    if not team:
        raise HTTPException(404, "Agent team not found")

    # Fetch agents for this team
    agents = session.exec(select(Agent).where(Agent.team_id == team.id)).all()
    return AgentTeamWithAgents(
        id=int(team.id) if team.id is not None else 0,
        name=team.name,
        description=team.description,
        created_at=team.created_at,
        agents=[
            AgentResponse(
                id=int(agent.id) if agent.id is not None else 0,
                name=agent.name,
                description=agent.description,
                default_prompt_version_id=agent.default_prompt_version_id,
                default_model_id=agent.default_model_id,
                team_id=agent.team_id,
                created_at=agent.created_at,
            )
            for agent in agents
        ],
    )


@router.put("/agent-teams/{team_id}", response_model=AgentTeamWithAgents)
def update_agent_team(
    team_id: int,
    team_data: AgentTeamUpdate,
    session: Annotated[Session, Depends(get_session)],
):
    team = session.get(AgentTeam, team_id)
    if not team:
        raise HTTPException(404, "Agent team not found")

    update_data = team_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)

    session.add(team)
    session.commit()
    session.refresh(team)

    # Fetch agents for the updated team
    agents = session.exec(select(Agent).where(Agent.team_id == team.id)).all()
    return AgentTeamWithAgents(
        id=int(team.id) if team.id is not None else 0,
        name=team.name,
        description=team.description,
        created_at=team.created_at,
        agents=[
            AgentResponse(
                id=int(agent.id) if agent.id is not None else 0,
                name=agent.name,
                description=agent.description,
                default_prompt_version_id=agent.default_prompt_version_id,
                default_model_id=agent.default_model_id,
                team_id=agent.team_id,
                created_at=agent.created_at,
            )
            for agent in agents
        ],
    )


@router.delete("/agent-teams/{team_id}")
def delete_agent_team(
    team_id: int,
    session: Annotated[Session, Depends(get_session)],
):
    team = session.get(AgentTeam, team_id)
    if not team:
        raise HTTPException(404, "Agent team not found")

    session.delete(team)
    session.commit()

    return {"message": "Agent team deleted successfully"}
