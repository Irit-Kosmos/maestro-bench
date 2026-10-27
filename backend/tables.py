# MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
# Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
# Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, Relationship, SQLModel

# Closed sets of values, enforced by CHECK constraints. Adding one takes a migration.
EXPERIMENT_STATUSES = (
    "pending",
    "queued",
    "running",
    "completed",
    "failed",
    "cancelled",
    "interrupted",
)
EXECUTION_STATUSES = ("running", "completed", "failed", "cancelled", "interrupted")
AGENT_KINDS = ("llm", "aggregator")
SAMPLING_TYPES = ("all", "random", "range")
TAGGED_KINDS = ("prompt", "analysis", "agent", "study")
STUDY_STATUSES = ("active", "concluded", "archived")
# What a study can gather, and what a note can be attached to (a study too)
STUDY_ITEM_KINDS = ("experiment", "batch", "analysis")
NOTE_KINDS = (*STUDY_ITEM_KINDS, "study")
# What a public link can point to
SHARE_KINDS = NOTE_KINDS
# From the least to the most powerful
ROLES = ("viewer", "editor", "owner")


class JsonText(TypeDecorator):
    """A jsonb column that the code reads and writes as JSON text.

    The database checks that what it stores is JSON, and can query it. The application
    keeps handling strings, as the API does: it parses them where it needs the value.
    Key order and spacing are the database's, not the writer's.
    """

    impl = JSONB
    cache_ok = True

    def __init__(self):
        # A missing value is SQL NULL, not a JSON null
        super().__init__(none_as_null=True)

    def process_bind_param(self, value, dialect):
        return None if value is None else json.loads(value)

    def process_result_value(self, value, dialect):
        return None if value is None else json.dumps(value, ensure_ascii=False)


# Every moment is stored with its time zone (timestamptz) and handled as an aware UTC datetime
TIMESTAMPTZ = DateTime(timezone=True)


def now_field():
    """A moment that defaults to now."""
    return Field(default_factory=lambda: datetime.now(UTC), sa_type=TIMESTAMPTZ)


def moment_field(**kwargs):
    """A moment that may be unknown yet (a completion, a use)."""
    return Field(default=None, sa_type=TIMESTAMPTZ, **kwargs)


def required_moment_field(**kwargs):
    """A moment the row cannot go without (an expiry)."""
    return Field(sa_type=TIMESTAMPTZ, **kwargs)


def _one_of(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


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
    created_at: datetime = now_field()


class Prompt(Authored, table=True):
    """Reusable prompts with versioning"""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # e.g., "Language Evaluator", "Content Scorer"
    description: str | None = None
    created_at: datetime = now_field()

    # Relationships
    versions: list["PromptVersion"] = Relationship(back_populates="prompt")


class PromptVersion(WorkspaceOwned, table=True):
    """Versioned prompt configurations - pure prompts without model coupling"""

    id: int | None = Field(default=None, primary_key=True)
    prompt_id: int = Field(foreign_key="prompt.id", index=True)
    version: str = Field(index=True)  # e.g., "1.0", "1.1", "2.0-beta"
    system_prompt: str | None = None
    user_prompt: str | None = None
    variables: str | None = Field(  # JSON of variable definitions
        default=None, sa_type=JsonText
    )

    # Metadata
    is_active: bool = Field(default=True)
    is_default: bool = Field(default=False)  # Default version for this prompt
    notes: str | None = None  # Version notes/changelog
    created_at: datetime = now_field()

    # Relationships
    prompt: Prompt | None = Relationship(back_populates="versions")


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
        default=None, foreign_key="promptversion.id", ondelete="SET NULL", index=True
    )
    default_model_id: int | None = Field(
        default=None, foreign_key="model.id", ondelete="SET NULL", index=True
    )

    created_at: datetime = now_field()

    __table_args__ = (
        CheckConstraint(_one_of("kind", AGENT_KINDS), name="ck_agent_kind"),
    )

    # Relationships
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
    created_at: datetime = now_field()

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
    base_experiment_id: int | None = Field(
        default=None, foreign_key="experiment.id", index=True
    )
    variations: str = Field(
        default="[]",
        sa_type=JsonText,
        description="JSON list of {step_key, agent_id, field, values} axes (cartesian product)",
    )
    # Seed of the random sample, shared by the batch's experiments so that they
    # all run on the same dataset rows
    sampling_seed: int | None = Field(default=None, sa_type=BigInteger)
    created_at: datetime = now_field()


class Experiment(Authored, table=True):
    """An experiment configuration using a dataset and a pipeline of agents"""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str | None = None
    dataset_id: int = Field(foreign_key="dataset.id", index=True)
    status: str = Field(
        default="pending"
    )  # pending, queued, running, completed, failed, cancelled, interrupted
    created_at: datetime = now_field()
    completed_at: datetime | None = moment_field()

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

    __table_args__ = (
        CheckConstraint(
            _one_of("status", EXPERIMENT_STATUSES), name="ck_experiment_status"
        ),
        CheckConstraint(
            "sampling_type IS NULL OR " + _one_of("sampling_type", SAMPLING_TYPES),
            name="ck_experiment_sampling_type",
        ),
        # The lists of a workspace, newest first
        Index("ix_experiment_workspace_created", "workspace_id", "created_at"),
        # What the dashboard shows as in progress
        Index(
            "ix_experiment_workspace_active",
            "workspace_id",
            postgresql_where=text("status IN ('pending', 'queued', 'running')"),
        ),
    )

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
    agent_id: int = Field(foreign_key="agent.id", index=True)
    # An agent may run several times in an experiment: each run is a step, told
    # apart by its key ("12", then "12#2"…), and named by its label
    step_key: str
    # None: the agent's own name
    label: str | None = None

    # Configuration (uses agent defaults if not specified)
    prompt_version_id: int | None = Field(
        default=None, foreign_key="promptversion.id", ondelete="SET NULL", index=True
    )
    model_id: int | None = Field(
        default=None, foreign_key="model.id", ondelete="SET NULL", index=True
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
        sa_type=JsonText,
        description="JSON string of per-agent input mappings",
    )
    # Aggregators: JSON list of {name, formula}
    formulas: str | None = Field(default=None, sa_type=JsonText)

    created_at: datetime = now_field()

    __table_args__ = (
        Index("idx_experiment_step_unique", "experiment_id", "step_key", unique=True),
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
    started_at: datetime = now_field()
    completed_at: datetime | None = moment_field()
    status: str = Field(default="running")  # running, completed, failed, cancelled, interrupted

    # Live progress, in dataset rows; rows_failed are counted in rows_done
    rows_total: int | None = None
    rows_done: int = 0
    rows_failed: int = 0

    # Dataset snapshot at execution time
    dataset_snapshot: str = Field(
        sa_type=JsonText,
        description="JSON snapshot of dataset metadata at execution"
    )

    # Results storage
    results_file_path: str | None = None

    # Aggregated metrics
    total_tokens: int | None = None
    total_cost_usd: float | None = None

    __table_args__ = (
        CheckConstraint(
            _one_of("status", EXECUTION_STATUSES), name="ck_experimentexecution_status"
        ),
        CheckConstraint(
            "rows_done >= 0 AND rows_failed >= 0",
            name="ck_experimentexecution_rows",
        ),
        # The executions of an experiment, newest first (also covers its foreign key)
        Index("ix_experimentexecution_experiment_started", "experiment_id", "started_at"),
        # Every execution of a workspace, newest first
        Index("ix_experimentexecution_workspace_started", "workspace_id", "started_at"),
    )

    # Relationships
    experiment: Experiment | None = Relationship(back_populates="executions")
    agent_snapshots: list["AgentExecutionSnapshot"] = Relationship(
        back_populates="execution",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class AgentExecutionSnapshot(WorkspaceOwned, table=True):
    """Immutable snapshot of each agent's configuration used during execution"""

    id: int | None = Field(default=None, primary_key=True)
    execution_id: int = Field(foreign_key="experimentexecution.id", index=True)
    # Empty once the agent is deleted: the snapshot keeps its name
    agent_id: int | None = Field(
        default=None, foreign_key="agent.id", ondelete="SET NULL", index=True
    )
    # Step of the experiment this one ran; empty on snapshots made before agents
    # could repeat, whose step is their agent
    step_key: str | None = None

    # Snapshot of configuration at execution time (exactly what was used).
    # Aggregators have no model nor prompt: those fields are empty strings.
    kind: str = Field(default="llm")
    agent_name_snapshot: str = Field(description="Name of the step at execution time")
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
    final_variables: str | None = Field(default=None, sa_type=JsonText)
    final_temperature: float | None = None
    final_max_tokens: int | None = None

    # Per-agent input mappings snapshot
    final_input_mappings: str | None = Field(
        default=None,
        sa_type=JsonText,
        description="JSON string of input mappings used at execution time",
    )
    # Aggregators: JSON list of {name, formula} used at execution time
    final_formulas: str | None = Field(default=None, sa_type=JsonText)

    execution_order: int = Field(description="Order in which this agent was executed")
    created_at: datetime = now_field()

    __table_args__ = (
        CheckConstraint(_one_of("kind", AGENT_KINDS), name="ck_agentexecutionsnapshot_kind"),
    )

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
    config: str = Field(sa_type=JsonText, description="JSON analysis configuration")
    runs: str = Field(
        sa_type=JsonText,
        description="JSON list of {execution_id, agent_name, label} to compare"
    )
    created_at: datetime = now_field()
    updated_at: datetime = now_field()


class Tag(Authored, table=True):
    """A label shared by every kind of item that can be tagged"""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # unique ignoring case, enforced by the API
    color: str = "gray"  # one of tags.TAG_COLORS
    created_at: datetime = now_field()

    __table_args__ = (
        Index("uq_tag_workspace_name", "workspace_id", text("lower(name)"), unique=True),
    )


class TagLink(WorkspaceOwned, table=True):
    """Puts a tag on an item: `kind` says which table `item_id` belongs to"""

    tag_id: int = Field(foreign_key="tag.id", primary_key=True)
    kind: str = Field(primary_key=True)  # "prompt" | "analysis" | "agent" | "study"
    item_id: int = Field(primary_key=True)

    __table_args__ = (
        CheckConstraint(_one_of("kind", TAGGED_KINDS), name="ck_taglink_kind"),
        # The tags of an item: the primary key starts with the tag
        Index("ix_taglink_kind_item", "kind", "item_id"),
    )


class Study(Authored, table=True):
    """A theme that gathers experiments, batches and analyses, with a journal of notes.

    A study only points to what it gathers: an item can belong to several studies,
    and deleting a study never deletes an item.
    """

    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str | None = None  # markdown
    status: str = "active"  # active, concluded, archived (read-only)
    created_at: datetime = now_field()
    # Moves when the study, its items or its notes change
    updated_at: datetime = now_field()

    __table_args__ = (
        CheckConstraint(_one_of("status", STUDY_STATUSES), name="ck_study_status"),
        # The lists of a workspace, most recently touched first
        Index("ix_study_workspace_updated", "workspace_id", "updated_at"),
    )


class StudyItem(WorkspaceOwned, table=True):
    """Puts an item in a study: `kind` says which table `item_id` belongs to"""

    study_id: int = Field(foreign_key="study.id", ondelete="CASCADE", primary_key=True)
    kind: str = Field(primary_key=True)  # "experiment" | "batch" | "analysis"
    item_id: int = Field(primary_key=True)
    added_at: datetime = now_field()
    added_by: int | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")

    __table_args__ = (
        CheckConstraint(_one_of("kind", STUDY_ITEM_KINDS), name="ck_studyitem_kind"),
        # The studies of an item: the primary key starts with the study
        Index("ix_studyitem_kind_item", "kind", "item_id"),
    )


class Note(Authored, table=True):
    """An entry of the journal of an item (or of a study): `created_by` is its author"""

    id: int | None = Field(default=None, primary_key=True)
    kind: str  # "experiment" | "batch" | "analysis" | "study"
    item_id: int
    body: str  # markdown
    created_at: datetime = now_field()
    updated_at: datetime = now_field()

    __table_args__ = (
        CheckConstraint(_one_of("kind", NOTE_KINDS), name="ck_note_kind"),
        # The journal of an item, in order
        Index("ix_note_kind_item_created", "kind", "item_id", "created_at"),
    )


class Share(WorkspaceOwned, table=True):
    """A public read-only link to an item: whoever holds the token sees the item.

    The token is kept as it is, not hashed: the author can see the link again.
    A revoked link stays, so that its page can say it is no longer active; the link
    of a deleted item goes with it. Like notes, it points to its item by kind and id.
    """

    id: int | None = Field(default=None, primary_key=True)
    kind: str  # "experiment" | "batch" | "analysis" | "study"
    item_id: int
    token: str = Field(unique=True, index=True)
    created_at: datetime = now_field()
    created_by: int | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    revoked_at: datetime | None = moment_field()
    revoked_by: int | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )

    __table_args__ = (
        CheckConstraint(_one_of("kind", SHARE_KINDS), name="ck_share_kind"),
        # One active link per item
        Index(
            "uq_share_active_item",
            "kind",
            "item_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )


class WorkspaceCredential(WorkspaceOwned, table=True):
    """The API key a workspace uses for a provider, encrypted (see `credentials`)"""

    __table_args__ = (UniqueConstraint("workspace_id", "provider"),)

    id: int | None = Field(default=None, primary_key=True)
    provider: str
    ciphertext: str = Field(exclude=True)
    last4: str  # the only part of the key that is ever shown again
    updated_at: datetime = now_field()
    updated_by: int | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )


class User(SQLModel, table=True):
    """A person who signs in, whatever the identity provider"""

    __tablename__ = "user"

    id: int | None = Field(default=None, primary_key=True)
    display_name: str
    email: str | None = None  # not unique: never a key
    avatar_url: str | None = None
    is_active: bool = Field(default=True)  # False signs the user out everywhere
    created_at: datetime = now_field()
    last_login_at: datetime | None = moment_field()

    # Users are looked up by email ignoring case
    __table_args__ = (Index("ix_user_email_lower", text("lower(email)")),)


class Identity(SQLModel, table=True):
    """An account of a user at an identity provider (GitLab...)"""

    __table_args__ = (UniqueConstraint("provider", "subject"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    provider: str  # "gitlab"
    subject: str  # the provider's stable id for the account
    email_at_login: str | None = None
    created_at: datetime = now_field()


class AuthSession(SQLModel, table=True):
    """A browser session; the cookie holds a token whose hash is the id"""

    __tablename__ = "session"

    id: str = Field(primary_key=True)  # sha256 of the cookie token
    user_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = now_field()
    last_seen_at: datetime = now_field()
    expires_at: datetime = required_moment_field()  # slides with activity
    absolute_expires_at: datetime = required_moment_field(index=True)  # never moves


class Workspace(SQLModel, table=True):
    """A space where people share models, prompts, datasets and experiments"""

    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)  # in the URLs
    name: str
    archived_at: datetime | None = moment_field()  # an archived workspace is read-only
    created_at: datetime = now_field()
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
    created_at: datetime = now_field()

    __table_args__ = (CheckConstraint(_one_of("role", ROLES), name="ck_membership_role"),)


class Invitation(SQLModel, table=True):
    """A link that lets anyone who opens it join a workspace with a given role"""

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(
        foreign_key="workspace.id", index=True, ondelete="CASCADE"
    )
    token_hash: str = Field(unique=True, index=True)  # sha256 of the token in the link
    role: str
    created_by: int | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    created_at: datetime = now_field()
    expires_at: datetime | None = moment_field()  # None: until it is revoked
    uses: int = 0  # people who joined through it
    revoked_at: datetime | None = moment_field()

    __table_args__ = (
        CheckConstraint(_one_of("role", ROLES), name="ck_invitation_role"),
    )
