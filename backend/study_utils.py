"""What studies and notes share: the items they point to, and the people behind them."""

from collections.abc import Iterable

from fastapi import HTTPException
from sqlmodel import Session, delete

from auth.workspaces import WorkspaceContext
from loading import by_id
from references import missing_ids
from schemas.notes import NoteResponse
from schemas.people import PersonResponse
from tables import Analysis, Batch, Experiment, Note, Study, StudyItem, User

# The tables a study gathers, and the ones a note can be about (a study too)
ITEM_TABLES: dict[str, type] = {
    "experiment": Experiment,
    "batch": Batch,
    "analysis": Analysis,
}
NOTE_TABLES: dict[str, type] = {**ITEM_TABLES, "study": Study}


def check_items_exist(session: Session, kind: str, item_ids: Iterable[int]) -> None:
    """Raise HTTP 422 unless every id is an item of that kind in the workspace."""
    if missing := missing_ids(session, ITEM_TABLES[kind], item_ids):
        raise HTTPException(status_code=422, detail=f"Unknown {kind}s: {missing}")


def clear_item_links(session: Session, kind: str, item_id: int) -> None:
    """Drop what points to an item that is being deleted: its studies and its notes.

    Nothing is committed.
    """
    session.exec(
        delete(StudyItem).where(StudyItem.kind == kind, StudyItem.item_id == item_id)
    )
    session.exec(delete(Note).where(Note.kind == kind, Note.item_id == item_id))


def people(
    session: Session, user_ids: Iterable[int | None]
) -> dict[int, PersonResponse]:
    """The people behind these user ids, in one query. Accounts that are gone are left out."""
    return {
        user_id: PersonResponse.model_validate(user)
        for user_id, user in by_id(session, User, user_ids).items()
    }


def note_responses(
    session: Session, notes: list[Note], context: WorkspaceContext
) -> list[NoteResponse]:
    """The notes as the caller sees them, with a single query for the authors."""
    authors = people(session, (n.created_by for n in notes))
    is_owner = context.can("owner")
    return [
        NoteResponse(
            id=int(note.id),
            kind=note.kind,
            item_id=note.item_id,
            body=note.body,
            author=authors.get(note.created_by) if note.created_by else None,
            created_at=note.created_at,
            updated_at=note.updated_at,
            can_edit=note.created_by == context.user_id,
            can_delete=is_owner or note.created_by == context.user_id,
        )
        for note in notes
    ]
