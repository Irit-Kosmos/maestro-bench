"""
Request and response models for prompts API
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class PromptCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None


class PromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class PromptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    created_at: datetime


class PromptVersionCreate(BaseModel):
    version: str
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    variables: Optional[str] = None
    model_id: Optional[int] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    is_active: bool = True
    is_default: bool = False
    notes: Optional[str] = None


class PromptVersionUpdate(BaseModel):
    version: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    variables: Optional[str] = None
    model_id: Optional[int] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    notes: Optional[str] = None


class PromptVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    prompt_id: int
    version: str
    system_prompt: Optional[str]
    user_prompt: Optional[str]
    variables: Optional[str]
    model_id: Optional[int]
    temperature: Optional[float]
    max_tokens: Optional[int]
    is_active: bool
    is_default: bool
    notes: Optional[str]
    created_at: datetime
