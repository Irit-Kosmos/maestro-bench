"""
Utility functions for dataset path handling
"""

import os
from pathlib import Path


def get_datasets_dir():
    """
    Get the datasets directory path, handling both container and local environments

    Returns:
        Path: The datasets directory path
    """
    # In container, datasets are mounted at /app/datasets
    if os.path.exists("/app/datasets"):
        return Path("/app/datasets")
    # For local development, use relative path from backend directory
    return Path(__file__).parent.parent / "datasets"


def get_dataset_file_path(file_path: str):
    """
    Get the full path to a dataset file

    Args:
        file_path: Relative path to the dataset file (e.g., "mohler_dataset.csv")

    Returns:
        Path: The full path to the dataset file
    """
    datasets_dir = get_datasets_dir()
    return datasets_dir / file_path


def validate_dataset_file(file_path: str):
    """
    Validate that a dataset file exists

    Args:
        file_path: Relative path to the dataset file

    Returns:
        Path: The full path to the dataset file

    Raises:
        FileNotFoundError: If the dataset file doesn't exist
    """
    full_path = get_dataset_file_path(file_path)
    if not full_path.exists():
        raise FileNotFoundError(
            f"Dataset file not found: {file_path} (looked in {full_path})"
        )
    return full_path
