"""
Request and response models for datasets API
"""

from __future__ import annotations

from datetime import datetime
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


class DatasetPreview(BaseModel):
    """What the file holds: its columns, its size and a few rows."""

    file_type: str
    headers: list[str]
    total_rows: int
    total_columns: int
    # JSON files may hold anything in a row, so a row is not always an object
    sample_data: list[Any] | None = None


class DatasetInfo(BaseModel):
    """A dataset with the size of its file, for configuring a sample."""

    id: int
    name: str
    description: str | None
    file_type: str
    headers: list[str]
    total_rows: int
    total_columns: int


class DatasetStats(BaseModel):
    id: int
    name: str
    description: str | None
    file_path: str | None
    created_at: datetime
    experiment_count: int


class DatasetRows(BaseModel):
    """Every row of a dataset file, to view and edit."""

    file_type: str
    headers: list[str]
    rows: list[dict[str, Any]]
    total_rows: int
    revision: str
    # Why the rows can be viewed but not saved, if so
    read_only_reason: str | None = None


class DatasetRowsSaved(BaseModel):
    revision: str
    total_rows: int
