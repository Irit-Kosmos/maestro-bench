from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class Model(SQLModel, table=True):
    """LLM models available for experiments"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # e.g., "gpt-4", "claude-3-opus", "mistral-large"
    provider: str  # e.g., "openai", "anthropic", "mistral"
    description: Optional[str] = None
    max_tokens: Optional[int] = None  # Model's context limit
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    prompt_versions: List["PromptVersion"] = Relationship(back_populates="model")


class Prompt(SQLModel, table=True):
    """Reusable prompts with versioning"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # e.g., "Language Evaluator", "Content Scorer"
    description: Optional[str] = None
    category: Optional[str] = None  # e.g., "evaluation", "generation", "analysis"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    versions: List["PromptVersion"] = Relationship(back_populates="prompt")


class PromptVersion(SQLModel, table=True):
    """Versioned prompt configurations"""
    id: Optional[int] = Field(default=None, primary_key=True)
    prompt_id: int = Field(foreign_key="prompt.id")
    version: str = Field(index=True)  # e.g., "1.0", "1.1", "2.0-beta"
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    variables: Optional[str] = None  # JSON string of variable definitions
    
    # Model-specific optimizations
    model_id: Optional[int] = Field(default=None, foreign_key="model.id")
    temperature: Optional[float] = Field(default=0.7)
    max_tokens: Optional[int] = None
    
    # Metadata
    is_active: bool = Field(default=True)
    is_default: bool = Field(default=False)  # Default version for this prompt
    notes: Optional[str] = None  # Version notes/changelog
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    prompt: Optional[Prompt] = Relationship(back_populates="versions")
    model: Optional[Model] = Relationship(back_populates="prompt_versions")


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
    """Individual agent that can be configured with prompts/models at experiment time"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # Human-readable name
    description: Optional[str] = None
    
    # Optional default prompt version and model (can be overridden in experiments)
    default_prompt_version_id: Optional[int] = Field(default=None, foreign_key="promptversion.id")
    default_model_id: Optional[int] = Field(default=None, foreign_key="model.id")
    
    team_id: int = Field(foreign_key="agentteam.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    team: Optional[AgentTeam] = Relationship(back_populates="agents")
    default_prompt_version: Optional[PromptVersion] = Relationship()
    default_model: Optional[Model] = Relationship()


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
    """Immutable snapshot of each agent's configuration used during execution"""
    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_execution_id: int = Field(foreign_key="experimentexecution.id")
    agent_id: int = Field(foreign_key="agent.id")
    
    # Snapshot of configuration at execution time
    agent_name_snapshot: str = Field(description="Agent name at execution time")
    model_name_snapshot: str = Field(description="Model name used")
    prompt_version_snapshot: str = Field(description="Prompt version used")
    
    # Actual configuration used (may include custom overrides)
    final_system_prompt: Optional[str] = None
    final_user_prompt: Optional[str] = None
    final_variables: Optional[str] = None  # JSON string
    final_temperature: Optional[float] = None
    final_max_tokens: Optional[int] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    experiment_execution: Optional[ExperimentExecution] = Relationship(back_populates="agent_executions")
    agent: Optional[Agent] = Relationship()


class ExperimentAgentConfig(SQLModel, table=True):
    """Configuration for an agent within a specific experiment"""
    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="experiment.id")
    agent_id: int = Field(foreign_key="agent.id")
    
    # Experiment-specific configuration (can override agent defaults)
    prompt_version_id: int = Field(foreign_key="promptversion.id")
    model_id: int = Field(foreign_key="model.id")
    
    # Optional overrides for model parameters
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    
    # Execution order and settings
    execution_order: int = Field(default=1)
    is_active: bool = Field(default=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    experiment: Optional[Experiment] = Relationship()
    agent: Optional[Agent] = Relationship()
    prompt_version: Optional[PromptVersion] = Relationship()
    model: Optional[Model] = Relationship()
