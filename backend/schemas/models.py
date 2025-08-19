"""
Request and response models for models API
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ModelCreate(BaseModel):
    name: str
    provider: str
    description: Optional[str] = None
    max_tokens: Optional[int] = None
    default_temperature: Optional[float] = 0.7
    default_max_tokens: Optional[int] = None
    is_active: bool = True


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    description: Optional[str] = None
    max_tokens: Optional[int] = None
    default_temperature: Optional[float] = None
    default_max_tokens: Optional[int] = None
    is_active: Optional[bool] = None


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    provider: str
    description: Optional[str]
    max_tokens: Optional[int]
    default_temperature: Optional[float]
    default_max_tokens: Optional[int]
    is_active: bool
    created_at: datetime
