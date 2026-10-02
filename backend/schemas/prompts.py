"""
Request and response models for prompts API
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from schemas.tags import TagResponse


class PromptCreate(BaseModel):
    name: str
    description: str | None = None
    category: str | None = None
    tag_ids: list[int] = []


class PromptUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    # Left out: the tags stay as they are. Sent: they become exactly these.
    tag_ids: list[int] | None = None


class PromptVersionCreate(BaseModel):
    version: str
    system_prompt: str | None = None
    user_prompt: str | None = None
    variables: str | None = None
    is_active: bool = True
    is_default: bool = False
    notes: str | None = None


class PromptVersionUpdate(BaseModel):
    version: str | None = None
    system_prompt: str | None = None
    user_prompt: str | None = None
    variables: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    notes: str | None = None


class PromptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    category: str | None
    created_at: datetime


class PromptDetail(PromptResponse):
    """A prompt with its tags (the tags are not read where a prompt only gives context)"""

    tags: list[TagResponse] = []


class PromptVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prompt_id: int
    version: str
    system_prompt: str | None
    user_prompt: str | None
    variables: str | None
    is_active: bool
    is_default: bool
    notes: str | None
    created_at: datetime
    prompt: PromptResponse | None = None


# Rebuild for forward references
PromptVersionResponse.model_rebuild()
