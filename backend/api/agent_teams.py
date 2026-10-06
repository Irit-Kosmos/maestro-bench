
from fastapi import APIRouter, HTTPException
from sqlmodel import select

from db import SessionDep
from loading import grouped_by
from schemas.agent_teams import (
    AgentResponse,
    AgentTeamCreate,
    AgentTeamUpdate,
    AgentTeamWithAgents,
)
from tables import Agent, AgentTeam

router = APIRouter(tags=["agent-teams"])


def _with_agents(team: AgentTeam, agents: list[Agent]) -> AgentTeamWithAgents:
    return AgentTeamWithAgents(
        id=int(team.id) if team.id is not None else 0,
        name=team.name,
        description=team.description,
        created_at=team.created_at,
        agents=[AgentResponse.from_agent(agent) for agent in agents],
    )


@router.get("/agent-teams", response_model=list[AgentTeamWithAgents])
def list_agent_teams(session: SessionDep):
    teams = session.exec(select(AgentTeam)).all()
    agents = grouped_by(
        session, Agent, Agent.team_id, [t.id for t in teams if t.id is not None]
    )
    return [_with_agents(team, agents[team.id]) for team in teams]


@router.post("/agent-teams", response_model=AgentTeamWithAgents, status_code=201)
def create_agent_team(
    team_data: AgentTeamCreate,
    session: SessionDep,
):
    team = AgentTeam(name=team_data.name, description=team_data.description)
    session.add(team)
    session.commit()
    session.refresh(team)

    return _with_agents(team, [])


@router.get("/agent-teams/{team_id}", response_model=AgentTeamWithAgents)
def get_agent_team(team_id: int, session: SessionDep):
    team = session.get(AgentTeam, team_id)
    if not team:
        raise HTTPException(404, "Agent team not found")

    agents = session.exec(select(Agent).where(Agent.team_id == team.id)).all()
    return _with_agents(team, list(agents))


@router.put("/agent-teams/{team_id}", response_model=AgentTeamWithAgents)
def update_agent_team(
    team_id: int,
    team_data: AgentTeamUpdate,
    session: SessionDep,
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

    agents = session.exec(select(Agent).where(Agent.team_id == team.id)).all()
    return _with_agents(team, list(agents))


@router.delete("/agent-teams/{team_id}", status_code=204)
def delete_agent_team(
    team_id: int,
    session: SessionDep,
):
    team = session.get(AgentTeam, team_id)
    if not team:
        raise HTTPException(404, "Agent team not found")

    session.delete(team)
    session.commit()

