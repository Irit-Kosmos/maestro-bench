import asyncio
import json
import secrets
from pathlib import Path
from typing import Annotated, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlmodel import Session, col, select

import config
import workspace_files
from dataset_rows import DatasetFileError, read_dataset_rows, write_dataset_rows
from dataset_utils import get_dataset_file_path, validate_dataset_file
from db import get_session
from schemas.datasets import DatasetCreate, DatasetRowsUpdate
from tables import Dataset, Experiment
from workspace_scope import current_workspace_id

router = APIRouter(tags=["datasets"])

# Number of sample rows returned by the /preview endpoint
_PREVIEW_ROWS = 5


# ---------------------------------------------------------------------------
# File-reading helper
# ---------------------------------------------------------------------------


def _read_dataset_metadata(file_path: Path, include_sample: bool = False) -> dict[str, Any]:
    """
    Read headers, row count, and optionally sample rows from a dataset file.
    Uses streaming / partial reads to avoid loading the full file into memory.
    """
    ext = file_path.suffix.lower()

    if ext == ".csv":
        # Count rows cheaply without loading all data
        with file_path.open("r", encoding="utf-8") as f:
            total_rows = sum(1 for _ in f) - 1  # subtract header

        header_df = pd.read_csv(file_path, nrows=0, skipinitialspace=True)
        headers = header_df.columns.tolist()

        sample_data = None
        if include_sample:
            sample_df = pd.read_csv(file_path, nrows=_PREVIEW_ROWS, skipinitialspace=True)
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
        return validate_dataset_file(dataset.workspace_id, dataset.file_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

_UPLOAD_EXTENSIONS = {".csv", ".json"}
_NAME_MAX_LENGTH = 200


def _check_uploaded_file(path: Path) -> None:
    """Refuse a file that could not be run as a dataset; the file is left in place."""
    try:
        content = read_dataset_rows(path)
    except DatasetFileError as e:
        raise HTTPException(e.status_code, e.detail) from e
    except (UnicodeDecodeError, ValueError) as e:
        kind = "UTF-8 CSV" if path.suffix == ".csv" else "JSON"
        raise HTTPException(400, f"The file is not a valid {kind} file") from e

    if content["read_only_reason"]:
        raise HTTPException(400, content["read_only_reason"])
    if not content["headers"]:
        raise HTTPException(400, "The file has no columns")
    if not content["rows"]:
        raise HTTPException(400, "The file has no rows")


async def _receive_upload(request: Request, destination: Path) -> None:
    """Write the request body to ``destination``, refusing a body over the limit."""
    limit = config.MAX_UPLOAD_MB * 1024 * 1024
    too_large = HTTPException(413, f"The file is larger than {config.MAX_UPLOAD_MB} MB")
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise too_large

    size = 0
    # "xb" never replaces a file: the name is random, a clash would be a bug
    with destination.open("xb") as out:
        async for chunk in request.stream():
            size += len(chunk)
            if size > limit:
                raise too_large
            out.write(chunk)
    if size == 0:
        raise HTTPException(400, "The file is empty")


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
    if dataset_data.file_path:
        try:
            get_dataset_file_path(current_workspace_id(session), dataset_data.file_path)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    dataset = Dataset(
        name=dataset_data.name,
        description=dataset_data.description,
        file_path=dataset_data.file_path,
    )
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


@router.post("/datasets/upload", response_model=Dataset, status_code=201)
async def upload_dataset(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    filename: Annotated[str, Query(min_length=1, max_length=255)],
    name: Annotated[str | None, Query(max_length=_NAME_MAX_LENGTH)] = None,
    description: Annotated[str | None, Query(max_length=2000)] = None,
):
    """
    Create a dataset from a CSV or JSON file sent as the raw request body.

    ``filename`` only tells the format and names the dataset: the file is stored
    under a name the server makes up, in the workspace's own folder.
    """
    extension = Path(filename).suffix.lower()
    if extension not in _UPLOAD_EXTENSIONS:
        raise HTTPException(400, "Only .csv and .json files can be uploaded")

    folder = workspace_files.datasets_dir(current_workspace_id(session))
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{secrets.token_hex(16)}{extension}"
    try:
        await _receive_upload(request, destination)
        await asyncio.to_thread(_check_uploaded_file, destination)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise

    dataset = Dataset(
        name=(name or "").strip() or Path(filename).stem[:_NAME_MAX_LENGTH],
        description=description,
        file_path=destination.name,
    )
    session.add(dataset)
    try:
        session.commit()
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
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
        raise HTTPException(500, f"Error reading dataset file: {e}") from e


@router.get("/datasets/{dataset_id}/rows")
def get_dataset_rows(
    dataset_id: int,
    session: Annotated[Session, Depends(get_session)],
):
    """Get every row of the dataset file, for viewing and editing."""
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    file_path = _resolve_dataset_file(dataset)
    try:
        return read_dataset_rows(file_path)
    except DatasetFileError as e:
        raise HTTPException(e.status_code, e.detail) from e
    except Exception as e:
        raise HTTPException(500, f"Error reading dataset file: {e}") from e


@router.put("/datasets/{dataset_id}/rows")
def update_dataset_rows(
    dataset_id: int,
    payload: DatasetRowsUpdate,
    session: Annotated[Session, Depends(get_session)],
):
    """Replace the rows of the dataset file. Columns stay as they are on disk."""
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    file_path = _resolve_dataset_file(dataset)
    try:
        return write_dataset_rows(file_path, payload.rows, payload.revision)
    except DatasetFileError as e:
        raise HTTPException(e.status_code, e.detail) from e
    except Exception as e:
        raise HTTPException(500, f"Error writing dataset file: {e}") from e


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
        raise HTTPException(500, f"Error reading dataset file: {e}") from e


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
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    # Checked before touching the file: a refused delete must not lose it
    used_by = session.exec(
        select(func.count()).where(col(Experiment.dataset_id) == dataset_id)
    ).one()
    if used_by:
        raise HTTPException(
            409, f"Dataset is used by {used_by} experiment(s); delete them first"
        )

    if dataset.file_path:
        try:
            file_path = get_dataset_file_path(dataset.workspace_id, dataset.file_path)
        except ValueError:
            file_path = None
        if file_path and file_path.is_file():
            file_path.unlink()

    session.delete(dataset)
    session.commit()
