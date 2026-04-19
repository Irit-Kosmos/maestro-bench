"""
Request and response models for datasets API
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    file_path: Optional[str] = None
