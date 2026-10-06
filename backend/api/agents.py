
from fastapi import APIRouter, HTTPException
from sqlalchemy import func
from sqlmodel import Session, col, select

from db import SessionDep
from references import missing_ids
from schemas.agent_teams import AgentCreate, AgentResponse, AgentUpdate
from tables import (
    Agent,
    AgentTeam,
    ExperimentAgentConfig,
    Model,
    PromptVersion,
)
from tag_utils import clear_item_tags, item_tags, set_item_tags, tags_by_item

router = APIRouter(tags=["agents"])


def _check_references(session: Session, fields: dict) -> None:
    """The team, prompt version and model an agent points to must be in the workspace."""
    for field, table, label in (
        ("team_id", AgentTeam, "Agent team"),
        ("default_prompt_version_id", PromptVersion, "Prompt version"),
        ("default_model_id", Model, "Model"),
    ):
        value = fields.get(field)
        if value is not None and missing_ids(session, table, [value]):
            raise HTTPException(422, f"{label} {value} not found")


@router.get("/agents", response_model=list[AgentResponse])
def list_agents(session: SessionDep):
    agents = session.exec(select(Agent)).all()
    tags = tags_by_item(session, "agent", [a.id for a in agents if a.id])
    return [AgentResponse.from_agent(a, tags.get(a.id or 0, [])) for a in agents]


@router.post("/agents", response_model=AgentResponse, status_code=201)
def create_agent(
    agent_data: AgentCreate,
    session: SessionDep,
):
    _check_references(session, agent_data.model_dump())
    agent = Agent(
        name=agent_data.name,
        description=agent_data.description,
        kind=agent_data.kind,
        default_prompt_version_id=agent_data.default_prompt_version_id,
        default_model_id=agent_data.default_model_id,
        team_id=agent_data.team_id,
    )
    session.add(agent)
    session.flush()
    set_item_tags(session, "agent", agent.id or 0, agent_data.tag_ids)
    session.commit()
    session.refresh(agent)
    return AgentResponse.from_agent(agent, item_tags(session, "agent", agent.id or 0))


@router.get("/agents/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: int, session: SessionDep):
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return AgentResponse.from_agent(agent, item_tags(session, "agent", agent_id))


@router.put("/agents/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: int,
    agent_data: AgentUpdate,
    session: SessionDep,
):
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")

    update_data = agent_data.model_dump(exclude_unset=True)
    _check_references(session, update_data)
    tag_ids = update_data.pop("tag_ids", None)
    for field, value in update_data.items():
        setattr(agent, field, value)
    if tag_ids is not None:
        set_item_tags(session, "agent", agent_id, tag_ids)

    session.add(agent)
    session.commit()
    session.refresh(agent)
    return AgentResponse.from_agent(agent, item_tags(session, "agent", agent_id))


@router.delete("/agents/{agent_id}", status_code=204)
def delete_agent(
    agent_id: int,
    session: SessionDep,
):
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")

    used_by = session.exec(
        select(func.count(func.distinct(ExperimentAgentConfig.experiment_id))).where(
            col(ExperimentAgentConfig.agent_id) == agent_id
        )
    ).one()
    if used_by:
        raise HTTPException(
            409, f"Agent is used by {used_by} experiment(s); delete them first"
        )

    clear_item_tags(session, "agent", agent_id)
    session.delete(agent)
    session.commit()

