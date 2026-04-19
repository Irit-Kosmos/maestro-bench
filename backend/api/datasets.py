import json
from pathlib import Path
from typing import Annotated, Dict, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from db import get_session
from tables import Dataset, Experiment
from dataset_utils import get_dataset_file_path, validate_dataset_file
from schemas.datasets import DatasetCreate

router = APIRouter(tags=["datasets"])

# Number of sample rows returned by the /preview endpoint
_PREVIEW_ROWS = 5


# ---------------------------------------------------------------------------
# File-reading helper
# ---------------------------------------------------------------------------


def _read_dataset_metadata(file_path: Path, include_sample: bool = False) -> Dict[str, Any]:
    """
    Read headers, row count, and optionally sample rows from a dataset file.
    Uses streaming / partial reads to avoid loading the full file into memory.
    """
    ext = file_path.suffix.lower()

    if ext == ".csv":
        # Count rows cheaply without loading all data
        with file_path.open("r", encoding="utf-8") as f:
            total_rows = sum(1 for _ in f) - 1  # subtract header

        header_df = pd.read_csv(file_path, nrows=0)
        headers = header_df.columns.tolist()

        sample_data = None
        if include_sample:
            sample_df = pd.read_csv(file_path, nrows=_PREVIEW_ROWS)
            sample_data = sample_df.to_dict("records")

        return {
            "file_type": "csv",
            "headers": headers,
            "total_rows": max(total_rows, 0),
            "total_columns": len(headers),
            "sample_data": sample_data,
        }

    elif ext == ".json":
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            headers = list(data[0].keys()) if data else []
            total_rows = len(data)
            sample_data = data[:_PREVIEW_ROWS] if include_sample else None
        elif isinstance(data, dict):
            headers = list(data.keys())
            total_rows = 1
            sample_data = [data] if include_sample else None
        else:
            headers = []
            total_rows = 0
            sample_data = [] if include_sample else None

        return {
            "file_type": "json",
            "headers": headers,
            "total_rows": total_rows,
            "total_columns": len(headers),
            "sample_data": sample_data,
        }

    raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")


def _resolve_dataset_file(dataset: Dataset) -> Path:
    """Validate dataset has a file_path and return the resolved Path."""
    if not dataset.file_path:
        raise HTTPException(status_code=400, detail="Dataset has no file path")
    try:
        return validate_dataset_file(dataset.file_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/datasets", response_model=list[Dataset])
def list_datasets(session: Annotated[Session, Depends(get_session)]):
    return session.exec(select(Dataset)).all()


@router.post("/datasets", response_model=Dataset, status_code=201)
def create_dataset(
    dataset_data: DatasetCreate,
    session: Annotated[Session, Depends(get_session)],
):
    dataset = Dataset(
        name=dataset_data.name,
        description=dataset_data.description,
        file_path=dataset_data.file_path,
    )
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


@router.get("/datasets/{dataset_id}", response_model=Dataset)
def get_dataset(dataset_id: int, session: Annotated[Session, Depends(get_session)]):
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    return dataset


@router.get("/datasets/{dataset_id}/preview")
def get_dataset_preview(
    dataset_id: int,
    session: Annotated[Session, Depends(get_session)],
):
    """Get a preview of the dataset including headers and first few rows."""
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    file_path = _resolve_dataset_file(dataset)
    try:
        return _read_dataset_metadata(file_path, include_sample=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error reading dataset file: {e}")


@router.get("/datasets/{dataset_id}/info")
def get_dataset_info(
    dataset_id: int, session: Annotated[Session, Depends(get_session)]
):
    """Get dataset information including row count for sampling configuration."""
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    file_path = _resolve_dataset_file(dataset)
    try:
        meta = _read_dataset_metadata(file_path, include_sample=False)
        return {
            "id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            **{k: meta[k] for k in ("file_type", "headers", "total_rows", "total_columns")},
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error reading dataset file: {e}")


@router.get("/datasets/{dataset_id}/stats", response_model=dict)
def get_dataset_stats(
    dataset_id: int, session: Annotated[Session, Depends(get_session)]
):
    """Get dataset with additional statistics including experiment count."""
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    experiment_count = len(
        session.exec(
            select(Experiment).where(Experiment.dataset_id == dataset_id)
        ).all()
    )

    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "file_path": dataset.file_path,
        "created_at": dataset.created_at,
        "experiment_count": experiment_count,
    }


@router.delete("/datasets/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: int, session: Annotated[Session, Depends(get_session)]):
    dataset = session.get(Dataset, dataset_id)
    if not dataset or dataset.file_path is None:
        raise HTTPException(404, "Dataset not found")

    file_path = get_dataset_file_path(dataset.file_path)
    if file_path.exists():
        file_path.unlink()

    session.delete(dataset)
    session.commit()
