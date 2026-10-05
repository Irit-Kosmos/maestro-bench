"""
Request and response models for tags API
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from tag_utils import TagColor, TaggedKind

NAME_MAX_LENGTH = 40


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    color: TagColor = "gray"


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    color: TagColor | None = None


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str


class TagAssign(BaseModel):
    """Tags to put on, and take off, several items at once. Their other tags are left alone."""

    kind: TaggedKind
    item_ids: list[int] = Field(min_length=1)
    add: list[int] = []
    remove: list[int] = []
