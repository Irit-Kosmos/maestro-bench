from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from db import get_session
from models import Agent
from schemas.agent_teams import AgentCreate, AgentUpdate

router = APIRouter(tags=["agents"])

@router.get("/agents", response_model=list[Agent])
def list_agents(session=Depends(get_session)):
    return session.exec(select(Agent)).all()

@router.post("/agents", response_model=Agent, status_code=201)
def create_agent(agent_data: AgentCreate, session=Depends(get_session)):
    agent = Agent(
        name=agent_data.name,
        description=agent_data.description,
        default_prompt_version_id=agent_data.default_prompt_version_id,
        default_model_id=agent_data.default_model_id,
        team_id=agent_data.team_id
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent

@router.get("/agents/{agent_id}", response_model=Agent)
def get_agent(agent_id: int, session=Depends(get_session)):
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent

@router.put("/agents/{agent_id}", response_model=Agent)
def update_agent(agent_id: int, agent_data: AgentUpdate, session=Depends(get_session)):
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    update_data = agent_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
    
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent

@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: int, session=Depends(get_session)):
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    session.delete(agent)
    session.commit()
    
    return {"message": "Agent deleted successfully"}
