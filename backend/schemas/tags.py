"""
Request and response models for tags API
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from tag_utils import TagColor

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


class TagWithCount(TagResponse):
    """A tag and how many items carry it, for the picker and the tags page"""

    count: int
