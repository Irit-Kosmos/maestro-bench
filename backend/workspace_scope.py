"""
Keeps every query and every insert inside one workspace.

A session is *scoped* by `scope_session`. From then on:

- every SELECT, UPDATE and DELETE on a `WorkspaceOwned` table only sees rows of
  that workspace, whatever the query says (joins, subqueries and relationship
  loads included), so a forgotten filter cannot leak another workspace's rows
  and another workspace's id simply isn't found;
- rows added to the session get the workspace (and the author) filled in, and
  adding one that belongs to another workspace is an error.

A session that is not scoped sees everything. That is for code that has no
workspace yet (migrations, the CLI, the first lookup of a background job), and it
cannot insert workspace-owned rows.
"""

from functools import cache

from sqlalchemy import event
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria
from sqlmodel import SQLModel

from tables import Authored, WorkspaceOwned

_WORKSPACE = "workspace_id"
_USER = "user_id"


@cache
def _owned_tables() -> tuple[type[WorkspaceOwned], ...]:
    """Every table whose rows belong to a workspace, whatever gets added later."""
    return tuple(
        mapper.class_
        for mapper in SQLModel._sa_registry.mappers
        if issubclass(mapper.class_, WorkspaceOwned)
    )


def scope_session(session: Session, workspace_id: int, user_id: int | None = None):
    """Confine the session to a workspace; `user_id` is recorded as the author."""
    session.info[_WORKSPACE] = workspace_id
    session.info[_USER] = user_id
    return session


@event.listens_for(Session, "do_orm_execute")
def _only_this_workspace(state: ORMExecuteState) -> None:
    workspace_id = state.session.info.get(_WORKSPACE)
    if workspace_id is None:
        return
    if state.is_select or state.is_update or state.is_delete:
        state.statement = state.statement.options(
            *(
                with_loader_criteria(
                    table, table.workspace_id == workspace_id, include_aliases=True
                )
                for table in _owned_tables()
            )
        )


@event.listens_for(Session, "before_flush")
def _own_new_rows(session: Session, flush_context, instances) -> None:
    workspace_id = session.info.get(_WORKSPACE)
    user_id = session.info.get(_USER)
    for row in session.new:
        if not isinstance(row, WorkspaceOwned):
            continue
        if workspace_id is None and row.workspace_id is None:
            raise RuntimeError(
                f"{type(row).__name__} belongs to a workspace: scope the session first"
            )
        if row.workspace_id is None:
            row.workspace_id = workspace_id
        elif workspace_id is not None and row.workspace_id != workspace_id:
            raise RuntimeError(
                f"{type(row).__name__} of workspace {row.workspace_id} added to a "
                f"session scoped to workspace {workspace_id}"
            )
        if isinstance(row, Authored) and row.created_by is None:
            row.created_by = user_id
