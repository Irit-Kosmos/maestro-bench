"""
Request and response models for studies API
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from schemas.notes import NoteResponse
from schemas.people import PersonResponse
from schemas.tags import TagResponse

StudyKind = Literal["experiment", "batch", "analysis"]
StudyStatus = Literal["active", "concluded", "archived"]

NAME_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 20_000


class StudyItemRef(BaseModel):
    kind: StudyKind
    item_id: int


class StudyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    tag_ids: list[int] = []
    # Items to put in the study from the start (a study made from a selection)
    items: list[StudyItemRef] = []


class StudyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: StudyStatus | None = None
    tag_ids: list[int] | None = None


class StudyItemsAdd(BaseModel):
    items: list[StudyItemRef] = Field(min_length=1)


class StudyAssign(BaseModel):
    """Put items in several studies, take them out, or both, in one go."""

    kind: StudyKind
    item_ids: list[int] = Field(min_length=1)
    add: list[int] = []
    remove: list[int] = []


class StudyMembership(BaseModel):
    study_id: int
    item_id: int


class StudyCounts(BaseModel):
    """What a study gathers, as it was put in (a batch is one item, not its experiments)."""

    experiments: int = 0
    batches: int = 0
    analyses: int = 0


class StudyResponse(BaseModel):
    id: int
    name: str
    description: str | None
    status: StudyStatus
    tags: list[TagResponse] = []
    author: PersonResponse | None = None
    counts: StudyCounts
    # Over the experiments of the study, those of its batches included and each
    # counted once. The tokens and cost add up the latest execution of each.
    execution_count: int = 0
    total_tokens: int | None = None
    total_cost_usd: float | None = None
    created_at: datetime
    updated_at: datetime


class StudyItemResponse(BaseModel):
    kind: StudyKind
    item_id: int
    name: str
    # An experiment's status, a batch's overall status; an analysis has none
    status: str | None = None
    dataset_name: str | None = None
    # Experiments of a batch
    experiment_count: int | None = None
    execution_count: int = 0
    total_tokens: int | None = None
    total_cost_usd: float | None = None
    created_at: datetime
    added_at: datetime
    added_by: PersonResponse | None = None


class StudyDetailResponse(StudyResponse):
    # Most recently added first
    items: list[StudyItemResponse]


class ActivityItem(BaseModel):
    kind: Literal["experiment", "batch", "analysis", "study"]
    item_id: int
    name: str


class ActivityEvent(BaseModel):
    """One line of a study's timeline, worked out from what the study already holds."""

    type: Literal["note", "item_added", "experiment_completed"]
    at: datetime
    actor: PersonResponse | None = None
    item: ActivityItem | None = None
    # For "note": the note itself, whether it is about the study or one of its items
    note: NoteResponse | None = None
