from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Index


class Model(SQLModel, table=True):
    """LLM models available for experiments"""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # e.g., "gpt-4", "claude-3-opus", "mistral-large"
    provider: str  # e.g., "openai", "anthropic", "mistral"
    description: Optional[str] = None
    max_tokens: Optional[int] = None  # Model's context limit

    # Default model parameters (can be overridden in experiments)
    default_temperature: Optional[float] = Field(default=0)
    default_max_tokens: Optional[int] = None

    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


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
    """Versioned prompt configurations - pure prompts without model coupling"""

    id: Optional[int] = Field(default=None, primary_key=True)
    prompt_id: int = Field(foreign_key="prompt.id")
    version: str = Field(index=True)  # e.g., "1.0", "1.1", "2.0-beta"
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    variables: Optional[str] = None  # JSON string of variable definitions

    # Metadata
    is_active: bool = Field(default=True)
    is_default: bool = Field(default=False)  # Default version for this prompt
    notes: Optional[str] = None  # Version notes/changelog
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    prompt: Optional[Prompt] = Relationship(back_populates="versions")


class AgentTeam(SQLModel, table=True):
    """A team of agents that work together"""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    agents: List["Agent"] = Relationship(
        back_populates="team", sa_relationship_kwargs={"lazy": "select"}
    )


class Agent(SQLModel, table=True):
    """Individual agent that can be configured with prompts/models at experiment time"""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # Human-readable name
    description: Optional[str] = None

    # Default configurations (can be overridden in experiments)
    default_prompt_version_id: Optional[int] = Field(
        default=None, foreign_key="promptversion.id"
    )
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
    file_path: Optional[str] = Field(
        default=None, description="Relative path to dataset file on disk"
    )
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

    # Dataset sampling configuration
    sampling_type: Optional[str] = Field(
        default=None, description="Type of sampling: 'all', 'random', 'range'"
    )
    sampling_size: Optional[int] = Field(
        default=None, description="Number of rows for random sampling"
    )
    sampling_start_row: Optional[int] = Field(
        default=None, description="Start row for range sampling (1-based)"
    )
    sampling_end_row: Optional[int] = Field(
        default=None, description="End row for range sampling (1-based, inclusive)"
    )

    # Column mapping configuration - stores how dataset columns map to prompt variables
    column_mappings: Optional[str] = Field(
        default=None, description="JSON string containing column mapping configuration"
    )

    # V2: Scoring configuration
    scoring_config: Optional[str] = Field(
        default=None,
        description="JSON string containing scoring configuration list",
    )

    # Relationships
    dataset: Optional[Dataset] = Relationship(back_populates="experiments")
    executions: List["ExperimentExecution"] = Relationship(
        back_populates="experiment",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    agent_configs: List["ExperimentAgentConfig"] = Relationship(
        back_populates="experiment",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class ExperimentAgentConfig(SQLModel, table=True):
    """Configuration for an agent within a specific experiment - this is the single source of truth"""

    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="experiment.id")
    agent_id: int = Field(foreign_key="agent.id")

    # Configuration (uses agent defaults if not specified)
    prompt_version_id: Optional[int] = Field(
        default=None, foreign_key="promptversion.id"
    )
    model_id: Optional[int] = Field(default=None, foreign_key="model.id")

    # Optional overrides for model parameters
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    # Execution settings
    execution_order: int = Field(default=1)
    is_active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Add unique constraint to prevent duplicate agent configurations per experiment
    __table_args__ = (
        Index("idx_experiment_agent_unique", "experiment_id", "agent_id", unique=True),
    )

    # Relationships
    experiment: Optional[Experiment] = Relationship(back_populates="agent_configs")
    agent: Optional[Agent] = Relationship()
    prompt_version: Optional[PromptVersion] = Relationship()
    model: Optional[Model] = Relationship()


class ExperimentExecution(SQLModel, table=True):
    """Immutable snapshot of an experiment execution for scientific reproducibility"""

    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="experiment.id")

    # Execution metadata
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = Field(default="running")  # running, completed, failed, cancelled

    # Dataset snapshot at execution time
    dataset_snapshot: str = Field(
        description="JSON snapshot of dataset metadata at execution"
    )

    # Results storage
    results_file_path: Optional[str] = None

    # V2: Aggregated metrics
    total_tokens: Optional[int] = None
    total_cost_usd: Optional[float] = None
    scores_summary: Optional[str] = None  # JSON string of {scorer_name: avg_score}

    # Relationships
    experiment: Optional[Experiment] = Relationship(back_populates="executions")
    agent_snapshots: List["AgentExecutionSnapshot"] = Relationship(
        back_populates="execution",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class AgentExecutionSnapshot(SQLModel, table=True):
    """Immutable snapshot of each agent's configuration used during execution"""

    id: Optional[int] = Field(default=None, primary_key=True)
    execution_id: int = Field(foreign_key="experimentexecution.id")
    agent_id: int = Field(foreign_key="agent.id")

    # Snapshot of configuration at execution time (exactly what was used)
    agent_name_snapshot: str = Field(description="Agent name at execution time")
    model_name_snapshot: str = Field(description="Model name used")
    model_provider_snapshot: str = Field(description="Model provider")
    prompt_name_snapshot: str = Field(description="Prompt name used")
    prompt_version_snapshot: str = Field(description="Prompt version used")

    # Actual configuration used (resolved from defaults + overrides)
    final_system_prompt: Optional[str] = None
    final_user_prompt: Optional[str] = None
    final_variables: Optional[str] = None  # JSON string
    final_temperature: Optional[float] = None
    final_max_tokens: Optional[int] = None

    execution_order: int = Field(description="Order in which this agent was executed")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    execution: Optional[ExperimentExecution] = Relationship(
        back_populates="agent_snapshots"
    )
    agent: Optional[Agent] = Relationship()
