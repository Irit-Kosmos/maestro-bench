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
Utility functions for dataset path handling.

Dataset files live in the workspace's ``datasets`` folder (see ``workspace_files``).
Dataset records only store a path relative to that folder.
"""

import csv
import json
from pathlib import Path

import pandas as pd

import workspace_files


def get_dataset_file_path(workspace_id: int, file_path: str) -> Path:
    """
    Resolve a dataset-relative path to an absolute path inside the workspace's
    datasets folder.

    Raises:
        ValueError: If the path escapes that folder (absolute path, ``..``
            components or a symbolic link).
    """
    try:
        return workspace_files.confine(
            workspace_files.datasets_dir(workspace_id), file_path
        )
    except ValueError as e:
        raise ValueError(
            f"Invalid dataset path: {file_path!r} must be relative to the datasets folder"
        ) from e


def validate_dataset_file(workspace_id: int, file_path: str) -> Path:
    """
    Resolve a dataset path and check that the file exists.

    Raises:
        ValueError: If the path escapes the workspace's datasets folder.
        FileNotFoundError: If the dataset file doesn't exist.
    """
    full_path = get_dataset_file_path(workspace_id, file_path)
    if not full_path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {file_path}")
    return full_path


def count_csv_rows(file_path: Path) -> int:
    """Number of data rows of a CSV file, counted without loading it."""
    with file_path.open("r", encoding="utf-8-sig", newline="") as f:
        records = sum(1 for record in csv.reader(f) if record)
    return max(records - 1, 0)


def dataset_shape(file_path: Path) -> tuple[list[str], int]:
    """Column names and number of rows of a dataset file."""
    if file_path.suffix.lower() == ".json":
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        rows = data if isinstance(data, list) else [data]
        headers = list(
            dict.fromkeys(key for row in rows if isinstance(row, dict) for key in row)
        )
        return headers, len(rows)
    with file_path.open("r", encoding="utf-8-sig", newline="") as f:
        headers = next(csv.reader(f), [])
    return headers, count_csv_rows(file_path)


def apply_column_map(df: pd.DataFrame, column_map: dict[str, str]) -> pd.DataFrame:
    """Rows of a dataset under the base dataset's column names.

    ``column_map`` is {base column: column of this dataset}. Each mapped column
    takes the base name; a column of this dataset that already has that name
    gives way to it. A mapped column is no longer there under its own name, unless
    the map keeps it (``{"text": "text"}``). The other columns stay as they are.
    """
    renamed = {base: df[column] for base, column in column_map.items() if column in df.columns}
    if not renamed:
        return df
    sources = set(column_map.values())
    kept = df.drop(columns=[c for c in df.columns if c in sources or c in renamed])
    return pd.concat([kept, pd.DataFrame(renamed, index=df.index)], axis=1)
