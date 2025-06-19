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
    
    # MAESTRO Integration fields
    agent_type: Optional[str] = None  # 'clarification', 'correction', 'probability', 'custom'
    default_content_prompt_id: Optional[int] = Field(foreign_key="prompttemplate.id", default=None)
    default_language_prompt_id: Optional[int] = Field(foreign_key="prompttemplate.id", default=None)
    default_model_config_id: Optional[int] = Field(foreign_key="modelconfig.id", default=None)
    default_weights: Optional[str] = None  # JSON array [content_weight, language_weight]
    
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
    
    # Store agent configurations as JSON for flexibility
    agent_configurations: Optional[str] = None  # JSON string of agent ID -> custom config mapping

    # Relationships
    dataset: Optional[Dataset] = Relationship(back_populates="experiments")
    experiment_configs: List["ExperimentConfig"] = Relationship(back_populates="experiment")
    executions: List["ExperimentExecution"] = Relationship(back_populates="experiment")


class ExperimentConfig(SQLModel, table=True):
    """Configuration linking an experiment to an agent team - simplified"""
    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="experiment.id")
    agent_team_id: int = Field(foreign_key="agentteam.id")
    
    # Execution settings
    active: bool = Field(default=True)
    priority: int = Field(default=1)  # Execution priority (1 = highest)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    experiment: Optional[Experiment] = Relationship(back_populates="experiment_configs")
    agent_team: Optional[AgentTeam] = Relationship(back_populates="experiment_configs")


class ExperimentExecution(SQLModel, table=True):
    """Captures the exact state of an experiment at execution time - immutable snapshot"""
    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="experiment.id")
    
    # Execution metadata
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = Field(default="running")  # running, completed, failed, cancelled
    
    # Dataset snapshot at execution time
    dataset_snapshot: str = Field(description="JSON snapshot of dataset metadata at execution")
    
    # Results storage
    results_file_path: Optional[str] = None  # Path to CSV/JSON results file from MAESTRO
    
    # Relationships
    experiment: Optional[Experiment] = Relationship(back_populates="executions")
    agent_executions: List["AgentExecutionConfig"] = Relationship(back_populates="experiment_execution")


class AgentExecutionConfig(SQLModel, table=True):
    """Immutable snapshot of each agent's EXACT configuration used during execution"""
    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_execution_id: int = Field(foreign_key="experimentexecution.id")
    agent_id: int = Field(foreign_key="agent.id")
    
    # Agent snapshot - exactly as it was during execution
    agent_name_snapshot: str = Field(description="Agent name at execution time")
    agent_team_id_snapshot: int = Field(description="Team ID at execution time")
    agent_team_name_snapshot: str = Field(description="Team name at execution time")
    
    # EXACT prompts and variables used (either original or custom overrides)
    final_system_prompt: Optional[str] = None  # The actual system prompt used
    final_user_prompt: Optional[str] = None    # The actual user prompt used
    final_variables: Optional[str] = None      # JSON of actual variables used
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    experiment_execution: Optional[ExperimentExecution] = Relationship(back_populates="agent_executions")
    agent: Optional[Agent] = Relationship()


# MAESTRO Integration Models
class ModelConfig(SQLModel, table=True):
    """Model configurations for MAESTRO experiments"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # e.g., "mistral-medium-default"
    model: str  # e.g., "mistral-medium-latest"
    temperature: float
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PromptTemplate(SQLModel, table=True):
    """Prompt templates for MAESTRO agents"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    type: str  # 'content', 'language', 'system', 'user'
    value: str = Field(description="The actual prompt text")
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
