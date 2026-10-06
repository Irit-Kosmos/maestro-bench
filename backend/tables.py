from datetime import UTC, datetime

from sqlalchemy import BigInteger, Index, UniqueConstraint, text
from sqlmodel import Field, Relationship, SQLModel


class WorkspaceOwned(SQLModel):
    """Rows that belong to one workspace.

    `workspace_id` is never set by hand: a session scoped to a workspace
    (see `workspace_scope`) fills it in on insert and only ever reads rows
    carrying it. Neither column is part of what the API returns.
    """

    workspace_id: int | None = Field(
        default=None,
        foreign_key="workspace.id",
        index=True,
        nullable=False,
        exclude=True,
    )


class Authored(WorkspaceOwned):
    """Top-level resources, which remember who created them."""

    created_by: int | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", exclude=True
    )


class Model(Authored, table=True):
    """LLM models available for experiments"""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # e.g., "gpt-4", "claude-3-opus", "mistral-large"
    provider: str  # e.g., "openai", "anthropic", "mistral"
    description: str | None = None
    max_tokens: int | None = None  # Model's context limit

    # Default model parameters (can be overridden in experiments)
    default_temperature: float | None = Field(default=0)
    default_max_tokens: int | None = None

    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Prompt(Authored, table=True):
    """Reusable prompts with versioning"""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # e.g., "Language Evaluator", "Content Scorer"
    description: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    versions: list["PromptVersion"] = Relationship(back_populates="prompt")


class PromptVersion(WorkspaceOwned, table=True):
    """Versioned prompt configurations - pure prompts without model coupling"""

    id: int | None = Field(default=None, primary_key=True)
    prompt_id: int = Field(foreign_key="prompt.id")
    version: str = Field(index=True)  # e.g., "1.0", "1.1", "2.0-beta"
    system_prompt: str | None = None
    user_prompt: str | None = None
    variables: str | None = None  # JSON string of variable definitions

    # Metadata
    is_active: bool = Field(default=True)
    is_default: bool = Field(default=False)  # Default version for this prompt
    notes: str | None = None  # Version notes/changelog
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    prompt: Prompt | None = Relationship(back_populates="versions")


class AgentTeam(Authored, table=True):
    """A team of agents that work together"""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    agents: list["Agent"] = Relationship(
        back_populates="team", sa_relationship_kwargs={"lazy": "select"}
    )


class Agent(WorkspaceOwned, table=True):
    """Individual agent that can be configured with prompts/models at experiment time"""

    id: int | None = Field(default=None, primary_key=True)
    name: str  # Human-readable name
    description: str | None = None
    # "llm" calls a model with a prompt; "aggregator" computes formulas from
    # other agents' outputs (core.formula)
    kind: str = Field(default="llm")

    # Default configurations (can be overridden in experiments)
    default_prompt_version_id: int | None = Field(
        default=None, foreign_key="promptversion.id", ondelete="SET NULL"
    )
    default_model_id: int | None = Field(
        default=None, foreign_key="model.id", ondelete="SET NULL"
    )

    team_id: int = Field(foreign_key="agentteam.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    team: AgentTeam | None = Relationship(back_populates="agents")
    default_prompt_version: PromptVersion | None = Relationship()
    default_model: Model | None = Relationship()


class Dataset(Authored, table=True):
    """Dataset containing questions/tasks for experiments"""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str | None = None
    file_path: str | None = Field(
        default=None, description="Relative path to dataset file on disk"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    experiments: list["Experiment"] = Relationship(back_populates="dataset")


class Batch(Authored, table=True):
    """A group of experiments generated from one base configuration.

    The experiments of a batch are ordinary, independent experiments: the batch
    only records how they were generated and keeps them together.
    """

    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str | None = None
    # Experiment the batch was derived from. Not part of the batch itself.
    base_experiment_id: int | None = Field(default=None, foreign_key="experiment.id")
    variations: str = Field(
        default="[]",
        description="JSON list of {agent_id, field, values} axes (cartesian product)",
    )
    # Seed of the random sample, shared by the batch's experiments so that they
    # all run on the same dataset rows
    sampling_seed: int | None = Field(default=None, sa_type=BigInteger)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Experiment(Authored, table=True):
    """An experiment configuration using a dataset and agent teams"""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str | None = None
    dataset_id: int = Field(foreign_key="dataset.id")
    status: str = Field(
        default="pending"
    )  # pending, queued, running, completed, failed, cancelled, interrupted
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    # Batch membership: the experiment's coordinates in the batch's grid, as
    # {"<agent_id>": {"<field>": value}}
    batch_id: int | None = Field(default=None, foreign_key="batch.id", index=True)
    variant: str | None = None

    # Dataset sampling configuration
    sampling_type: str | None = Field(
        default=None, description="Type of sampling: 'all', 'random', 'range'"
    )
    sampling_size: int | None = Field(
        default=None, description="Number of rows for random sampling"
    )
    sampling_start_row: int | None = Field(
        default=None, description="Start row for range sampling (1-based)"
    )
    sampling_end_row: int | None = Field(
        default=None, description="End row for range sampling (1-based, inclusive)"
    )
    # Seed of the random sample, kept so that every run takes the same rows until
    # the sample is redrawn. An experiment of a batch uses the batch's seed instead.
    sampling_seed: int | None = Field(default=None, sa_type=BigInteger)

    # Relationships
    dataset: Dataset | None = Relationship(back_populates="experiments")
    executions: list["ExperimentExecution"] = Relationship(
        back_populates="experiment",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    agent_configs: list["ExperimentAgentConfig"] = Relationship(
        back_populates="experiment",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class ExperimentAgentConfig(WorkspaceOwned, table=True):
    """Configuration for an agent within a specific experiment - this is the single source of truth"""

    id: int | None = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="experiment.id")
    agent_id: int = Field(foreign_key="agent.id")

    # Configuration (uses agent defaults if not specified)
    prompt_version_id: int | None = Field(
        default=None, foreign_key="promptversion.id", ondelete="SET NULL"
    )
    model_id: int | None = Field(
        default=None, foreign_key="model.id", ondelete="SET NULL"
    )

    # Optional overrides for model parameters
    temperature: float | None = None
    max_tokens: int | None = None

    # Execution settings
    execution_order: int = Field(default=1)
    is_active: bool = Field(default=True)

    # Per-agent input mappings: how dataset columns / previous agent outputs
    # map to this agent's prompt variables (or an aggregator's formula variables)
    input_mappings: str | None = Field(
        default=None,
        description="JSON string of per-agent input mappings",
    )
    # Aggregators: JSON list of {name, formula}
    formulas: str | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Add unique constraint to prevent duplicate agent configurations per experiment
    __table_args__ = (
        Index("idx_experiment_agent_unique", "experiment_id", "agent_id", unique=True),
    )

    # Relationships
    experiment: Experiment | None = Relationship(back_populates="agent_configs")
    agent: Agent | None = Relationship()
    prompt_version: PromptVersion | None = Relationship()
    model: Model | None = Relationship()


class ExperimentExecution(WorkspaceOwned, table=True):
    """Immutable snapshot of an experiment execution for scientific reproducibility"""

    id: int | None = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="experiment.id")

    # Execution metadata
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    status: str = Field(default="running")  # running, completed, failed, cancelled, interrupted

    # Live progress, in dataset rows; rows_failed are counted in rows_done
    rows_total: int | None = None
    rows_done: int = 0
    rows_failed: int = 0

    # Dataset snapshot at execution time
    dataset_snapshot: str = Field(
        description="JSON snapshot of dataset metadata at execution"
    )

    # Results storage
    results_file_path: str | None = None

    # Aggregated metrics
    total_tokens: int | None = None
    total_cost_usd: float | None = None

    # Relationships
    experiment: Experiment | None = Relationship(back_populates="executions")
    agent_snapshots: list["AgentExecutionSnapshot"] = Relationship(
        back_populates="execution",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class AgentExecutionSnapshot(WorkspaceOwned, table=True):
    """Immutable snapshot of each agent's configuration used during execution"""

    id: int | None = Field(default=None, primary_key=True)
    execution_id: int = Field(foreign_key="experimentexecution.id")
    # Empty once the agent is deleted: the snapshot keeps its name
    agent_id: int | None = Field(
        default=None, foreign_key="agent.id", ondelete="SET NULL"
    )

    # Snapshot of configuration at execution time (exactly what was used).
    # Aggregators have no model nor prompt: those fields are empty strings.
    kind: str = Field(default="llm")
    agent_name_snapshot: str = Field(description="Agent name at execution time")
    model_name_snapshot: str = Field(description="Model name used")
    model_provider_snapshot: str = Field(description="Model provider")
    prompt_name_snapshot: str = Field(description="Prompt name used")
    prompt_version_snapshot: str = Field(description="Prompt version used")
    # Where the prompt lives now, to link back to it; empty on snapshots made before these existed
    prompt_id: int | None = None
    prompt_version_id: int | None = None

    # Actual configuration used (resolved from defaults + overrides)
    final_system_prompt: str | None = None
    final_user_prompt: str | None = None
    final_variables: str | None = None  # JSON string
    final_temperature: float | None = None
    final_max_tokens: int | None = None

    # Per-agent input mappings snapshot
    final_input_mappings: str | None = Field(
        default=None,
        description="JSON string of input mappings used at execution time",
    )
    # Aggregators: JSON list of {name, formula} used at execution time
    final_formulas: str | None = None

    execution_order: int = Field(description="Order in which this agent was executed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    execution: ExperimentExecution | None = Relationship(
        back_populates="agent_snapshots"
    )
    agent: Agent | None = Relationship()


class Analysis(Authored, table=True):
    """
    A saved comparison of executions against a ground-truth column.

    Only the configuration is stored; metrics are recomputed from the
    (immutable) results files each time the analysis is opened.
    """

    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str | None = None
    config: str = Field(description="JSON analysis configuration")
    runs: str = Field(
        description="JSON list of {execution_id, agent_name, label} to compare"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Tag(Authored, table=True):
    """A label shared by every kind of item that can be tagged"""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # unique ignoring case, enforced by the API
    color: str = "gray"  # one of tags.TAG_COLORS
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("uq_tag_workspace_name", "workspace_id", text("lower(name)"), unique=True),
    )


class TagLink(WorkspaceOwned, table=True):
    """Puts a tag on an item: `kind` says which table `item_id` belongs to"""

    tag_id: int = Field(foreign_key="tag.id", primary_key=True)
    kind: str = Field(primary_key=True)  # "prompt" | "analysis" | "agent"
    item_id: int = Field(primary_key=True)


class WorkspaceCredential(WorkspaceOwned, table=True):
    """The API key a workspace uses for a provider, encrypted (see `credentials`)"""

    __table_args__ = (UniqueConstraint("workspace_id", "provider"),)

    id: int | None = Field(default=None, primary_key=True)
    provider: str
    ciphertext: str = Field(exclude=True)
    last4: str  # the only part of the key that is ever shown again
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_by: int | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )


class User(SQLModel, table=True):
    """A person who signs in, whatever the identity provider"""

    __tablename__ = "user"

    id: int | None = Field(default=None, primary_key=True)
    display_name: str
    email: str | None = Field(default=None, index=True)  # not unique: never a key
    avatar_url: str | None = None
    is_active: bool = Field(default=True)  # False signs the user out everywhere
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_login_at: datetime | None = None


class Identity(SQLModel, table=True):
    """An account of a user at an identity provider (GitLab...)"""

    __table_args__ = (UniqueConstraint("provider", "subject"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    provider: str  # "gitlab"
    subject: str  # the provider's stable id for the account
    email_at_login: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuthSession(SQLModel, table=True):
    """A browser session; the cookie holds a token whose hash is the id"""

    __tablename__ = "session"

    id: str = Field(primary_key=True)  # sha256 of the cookie token
    user_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime  # slides with activity
    absolute_expires_at: datetime  # never moves


class Workspace(SQLModel, table=True):
    """A space where people share models, prompts, datasets and experiments"""

    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)  # in the URLs
    name: str
    archived_at: datetime | None = None  # an archived workspace is read-only
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: int | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )


class Membership(SQLModel, table=True):
    """What a user can do in a workspace: `owner` > `editor` > `viewer`"""

    workspace_id: int = Field(
        foreign_key="workspace.id", primary_key=True, ondelete="CASCADE"
    )
    user_id: int = Field(
        foreign_key="user.id", primary_key=True, index=True, ondelete="CASCADE"
    )
    role: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Invitation(SQLModel, table=True):
    """A link that lets one person join a workspace with a given role"""

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(
        foreign_key="workspace.id", index=True, ondelete="CASCADE"
    )
    token_hash: str = Field(unique=True, index=True)  # sha256 of the token in the link
    role: str
    created_by: int | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime
    used_at: datetime | None = None
    used_by: int | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    revoked_at: datetime | None = None
