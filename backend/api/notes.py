from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select

from auth.workspaces import WorkspaceContext, workspace_context
from db import SessionDep
from schemas.notes import NoteCreate, NoteKind, NoteResponse, NoteUpdate
from study_utils import NOTE_TABLES, note_responses
from tables import Note, Study

router = APIRouter(tags=["notes"])

ContextDep = Annotated[WorkspaceContext, Depends(workspace_context)]


def _check_item(session: Session, kind: str, item_id: int) -> None:
    if session.get(NOTE_TABLES[kind], item_id) is None:
        raise HTTPException(status_code=404, detail=f"{kind.capitalize()} not found")


def _writable_study(session: Session, kind: str, item_id: int) -> Study | None:
    """The study a note is about, if it is about one: an archived study is read-only."""
    if kind != "study":
        return None
    study = session.get(Study, item_id)
    if study and study.status == "archived":
        raise HTTPException(
            status_code=409, detail="This study is archived: it is read-only"
        )
    return study


def _get_note(session: Session, note_id: int) -> Note:
    note = session.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.get("/notes", response_model=list[NoteResponse])
def list_notes(
    kind: NoteKind,
    item_id: int,
    session: SessionDep,
    context: ContextDep,
):
    """The journal of an item (or of a study), newest first."""
    _check_item(session, kind, item_id)
    notes = session.exec(
        select(Note)
        .where(Note.kind == kind, Note.item_id == item_id)
        .order_by(col(Note.created_at).desc(), col(Note.id).desc())
    ).all()
    return note_responses(session, list(notes), context)


@router.post("/notes", response_model=NoteResponse, status_code=201)
def create_note(data: NoteCreate, session: SessionDep, context: ContextDep):
    _check_item(session, data.kind, data.item_id)
    study = _writable_study(session, data.kind, data.item_id)
    now = datetime.now(UTC)
    note = Note(
        kind=data.kind,
        item_id=data.item_id,
        body=data.body,
        created_at=now,
        updated_at=now,
    )
    session.add(note)
    if study:
        study.updated_at = now
        session.add(study)
    session.commit()
    session.refresh(note)
    return note_responses(session, [note], context)[0]


@router.put("/notes/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: int, data: NoteUpdate, session: SessionDep, context: ContextDep
):
    """Only the author edits a note."""
    note = _get_note(session, note_id)
    if note.created_by != context.user_id:
        raise HTTPException(status_code=403, detail="Only the author can edit a note")
    _writable_study(session, note.kind, note.item_id)
    note.body = data.body
    note.updated_at = datetime.now(UTC)
    session.add(note)
    session.commit()
    session.refresh(note)
    return note_responses(session, [note], context)[0]


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int, session: SessionDep, context: ContextDep):
    """The author deletes a note, and so does an owner of the workspace."""
    note = _get_note(session, note_id)
    if note.created_by != context.user_id and not context.can("owner"):
        raise HTTPException(
            status_code=403, detail="Only the author or an owner can delete a note"
        )
    _writable_study(session, note.kind, note.item_id)
    session.delete(note)
    session.commit()
