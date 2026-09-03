"""
Request and response models for datasets API
"""

from __future__ import annotations

from pydantic import BaseModel


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None
    file_path: str | None = None
