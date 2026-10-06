"""
Request and response models for notes API
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from schemas.people import PersonResponse

NoteKind = Literal["experiment", "batch", "analysis", "study"]

BODY_MAX_LENGTH = 50_000


def _not_blank(body: str) -> str:
    if not body.strip():
        raise ValueError("A note cannot be empty")
    return body


class NoteCreate(BaseModel):
    kind: NoteKind
    item_id: int
    body: str = Field(min_length=1, max_length=BODY_MAX_LENGTH)  # markdown

    _body_not_blank = field_validator("body")(_not_blank)


class NoteUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=BODY_MAX_LENGTH)

    _body_not_blank = field_validator("body")(_not_blank)


class NoteResponse(BaseModel):
    id: int
    kind: NoteKind
    item_id: int
    body: str
    # None when the author's account is gone
    author: PersonResponse | None = None
    created_at: datetime
    updated_at: datetime
    # What the caller may do with it: only the author edits, the author or an owner deletes
    can_edit: bool
    can_delete: bool
