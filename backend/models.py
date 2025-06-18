from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class AgentTeam(SQLModel, table=True):
    """A team of agents that work together"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    agents: List["Agent"] = Relationship(back_populates="team", sa_relationship_kwargs={"lazy": "select"})
    experiment_configs: List["ExperimentConfig"] = Relationship(back_populates="agent_team", sa_relationship_kwargs={"lazy": "select"})


class Agent(SQLModel, table=True):
    """Individual agent with specific prompts and behavior"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # Human-readable name
    description: Optional[str] = None
    system_prompt: Optional[str] = None  # System prompt for the agent
    user_prompt: Optional[str] = None  # User prompt template with variables
    variables: Optional[str] = None  # JSON string of variable definitions
    team_id: int = Field(foreign_key="agentteam.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    team: Optional[AgentTeam] = Relationship(back_populates="agents")


class Dataset(SQLModel, table=True):
    """Dataset containing questions/tasks for experiments"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    file_path: Optional[str] = Field(default=None, description="Relative path to dataset file on disk")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    experiments: List["Experiment"] = Relationship(back_populates="dataset")


class Experiment(SQLModel, table=True):
    """An experiment configuration using a dataset and agent teams"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    dataset_id: int = Field(foreign_key="dataset.id")
    status: str = Field(default="pending")  # pending, running, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Relationships
    dataset: Optional[Dataset] = Relationship(back_populates="experiments")
    experiment_configs: List["ExperimentConfig"] = Relationship(back_populates="experiment")


class ExperimentConfig(SQLModel, table=True):
    """Configuration linking an experiment to an agent team with custom settings"""
    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="experiment.id")
    agent_team_id: int = Field(foreign_key="agentteam.id")
    
    # Customization options
    custom_system_prompt: Optional[str] = None  # Override system prompts for all agents in team
    custom_user_prompt: Optional[str] = None    # Override user prompts for all agents in team
    custom_variables: Optional[str] = None      # JSON string of custom variables
    
    # Execution settings
    active: bool = Field(default=True)
    priority: int = Field(default=1)  # Execution priority (1 = highest)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    experiment: Optional[Experiment] = Relationship(back_populates="experiment_configs")
    agent_team: Optional[AgentTeam] = Relationship(back_populates="experiment_configs")
