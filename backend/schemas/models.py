"""
Request and response models for models API
"""

from __future__ import annotations

from pydantic import BaseModel


class ModelCreate(BaseModel):
    name: str
    provider: str
    description: str | None = None
    max_tokens: int | None = None
    default_temperature: float | None = 0.7
    default_max_tokens: int | None = None
    is_active: bool = True


class ModelUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    description: str | None = None
    max_tokens: int | None = None
    default_temperature: float | None = None
    default_max_tokens: int | None = None
    is_active: bool | None = None



