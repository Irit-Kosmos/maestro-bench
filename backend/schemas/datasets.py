"""
Request and response models for datasets API
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None
    file_path: str | None = None


class DatasetRowsUpdate(BaseModel):
    rows: list[dict[str, Any]]
    # Revision returned when the rows were read, to detect concurrent changes
    revision: str
