"""Archiving and deleting a workspace."""

import shutil
from datetime import UTC, datetime

from sqlalchemy import delete, update
from sqlmodel import Session, col, select

import async_jobs
import workspace_files
from auth import invitations
from tables import (
    Agent,
    AgentExecutionSnapshot,
    AgentTeam,
    Analysis,
    Batch,
    Dataset,
    Experiment,
    ExperimentAgentConfig,
    ExperimentExecution,
    Invitation,
    Membership,
    Model,
    Note,
    Prompt,
    PromptVersion,
    Study,
    StudyItem,
    Tag,
    TagLink,
    Workspace,
    WorkspaceCredential,
)

# What a workspace owns, children before the rows they point to. The two links that
# make a loop (a batch's base experiment, an experiment's batch) are cut first.
DELETE_ORDER = (
    TagLink,
    StudyItem,
    Note,
    Study,
    AgentExecutionSnapshot,
    ExperimentAgentConfig,
    ExperimentExecution,
    Analysis,
    WorkspaceCredential,
    Experiment,
    Batch,
    Dataset,
    Agent,
    AgentTeam,
    Model,
    PromptVersion,
    Prompt,
    Tag,
)


def archive(db: Session, workspace: Workspace) -> None:
    """Make a workspace read-only: its runs stop, its API keys and invitations go."""
    in_flight = db.exec(
        select(Experiment.id).where(
            Experiment.workspace_id == workspace.id,
            col(Experiment.status).in_(("running", "queued")),
        )
    ).all()
    for experiment_id in in_flight:
        async_jobs.cancel_experiment(experiment_id)

    db.execute(
        delete(WorkspaceCredential).where(WorkspaceCredential.workspace_id == workspace.id)
    )
    invitations.revoke_all(db, workspace.id)
    workspace.archived_at = datetime.now(UTC)
    db.add(workspace)
    db.commit()


def unarchive(db: Session, workspace: Workspace) -> None:
    """Make an archived workspace writable again (its API keys are not restored)."""
    workspace.archived_at = None
    db.add(workspace)
    db.commit()


def delete_workspace(db: Session, workspace: Workspace) -> None:
    """Remove a workspace with everything in it, files included."""
    workspace_id = workspace.id
    db.execute(update(Batch).where(Batch.workspace_id == workspace_id).values(base_experiment_id=None))
    db.execute(update(Experiment).where(Experiment.workspace_id == workspace_id).values(batch_id=None))
    for table in DELETE_ORDER:
        db.execute(delete(table).where(table.workspace_id == workspace_id))
    db.execute(delete(Invitation).where(Invitation.workspace_id == workspace_id))
    db.execute(delete(Membership).where(Membership.workspace_id == workspace_id))
    db.execute(delete(Workspace).where(Workspace.id == workspace_id))
    db.commit()
    # After the commit: a failure above must not leave a workspace without its files
    shutil.rmtree(workspace_files.workspace_dir(workspace_id), ignore_errors=True)
