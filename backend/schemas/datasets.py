"""
Request and response models for datasets API
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

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


class AgreementMetricInfo(BaseModel):
    key: str
    label: str
    description: str


class AgreementValueResponse(BaseModel):
    value: float | None
    undefined_reason: str | None


class AgreementColumnResponse(BaseModel):
    column: str
    # Rows with a usable value, and rows left out because blank or invalid
    n: int
    n_missing: int
    # Numeric columns only
    mean: float | None


class AgreementPairResponse(BaseModel):
    a: str
    b: str
    # Rows rated by both columns
    n: int
    metrics: dict[str, AgreementValueResponse]


class AgreementOverallResponse(BaseModel):
    # Rows rated by at least two columns
    n_items: int
    # Share of those rows where every rating is the same
    unanimous: float | None
    alpha: AgreementValueResponse


class DatasetAgreement(BaseModel):
    """How much the selected columns agree on the rows of a dataset."""

    value_type: Literal["numeric", "categorical"]
    n_rows: int
    metrics: list[AgreementMetricInfo]
    columns: list[AgreementColumnResponse]
    pairs: list[AgreementPairResponse]
    overall: AgreementOverallResponse
    warnings: list[str]
