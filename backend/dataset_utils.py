"""
Utility functions for dataset path handling.

Dataset files live in the top-level ``datasets/`` directory (next to
``backend/`` and ``frontend/``). Dataset records only store a path relative
to that directory.
"""

import csv
from pathlib import Path


def get_datasets_dir() -> Path:
    """Return the datasets directory (one level above the backend directory)."""
    return (Path(__file__).parent.parent / "datasets").resolve()


def get_dataset_file_path(file_path: str) -> Path:
    """
    Resolve a dataset-relative path to an absolute path inside the datasets
    directory.

    Raises:
        ValueError: If the path escapes the datasets directory
            (absolute path or ``..`` components).
    """
    datasets_dir = get_datasets_dir()
    full_path = (datasets_dir / file_path).resolve()
    if datasets_dir not in full_path.parents:
        raise ValueError(
            f"Invalid dataset path: {file_path!r} must be relative to the datasets directory"
        )
    return full_path


def validate_dataset_file(file_path: str) -> Path:
    """
    Resolve a dataset path and check that the file exists.

    Raises:
        ValueError: If the path escapes the datasets directory.
        FileNotFoundError: If the dataset file doesn't exist.
    """
    full_path = get_dataset_file_path(file_path)
    if not full_path.is_file():
        raise FileNotFoundError(
            f"Dataset file not found: {file_path} (looked in {full_path})"
        )
    return full_path


def count_csv_rows(file_path: Path) -> int:
    """Number of data rows of a CSV file, counted without loading it."""
    with file_path.open("r", encoding="utf-8-sig", newline="") as f:
        records = sum(1 for record in csv.reader(f) if record)
    return max(records - 1, 0)
