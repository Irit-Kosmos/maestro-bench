# MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
# Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
# Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Request and response models for datasets API
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

NAME_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 2000


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None
    file_path: str | None = None


class DatasetUpdate(BaseModel):
    """What can be renamed or described; the file is changed through its rows."""

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)


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
