from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from db import get_session
from models import Dataset
from dataset_utils import get_dataset_file_path, validate_dataset_file
import pandas as pd
import json
import os
from pathlib import Path

router = APIRouter(tags=["datasets"])

@router.get("/datasets", response_model=list[Dataset])
def list_datasets(session=Depends(get_session)):
    return session.exec(select(Dataset)).all()

@router.post("/datasets", response_model=Dataset, status_code=201)
def create_dataset(dataset: Dataset, session=Depends(get_session)):
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset

@router.get("/datasets/{dataset_id}", response_model=Dataset)
def get_dataset(dataset_id: int, session=Depends(get_session)):
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    return dataset

@router.get("/datasets/{dataset_id}/preview")
def get_dataset_preview(dataset_id: int, session=Depends(get_session)):
    """
    Get a preview of the dataset including headers and first few rows
    """
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    
    if not dataset.file_path:
        raise HTTPException(400, "Dataset has no file path")
    
    # Construct the full path to the dataset file
    try:
        file_path = validate_dataset_file(dataset.file_path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    
    try:
        file_extension = file_path.suffix.lower()
        
        if file_extension == '.csv':
            # Read CSV file
            df = pd.read_csv(file_path)
            headers = df.columns.tolist()
            sample_data = df.head(5).to_dict('records')
            total_rows = len(df)
            
            return {
                "file_type": "csv",
                "headers": headers,
                "sample_data": sample_data,
                "total_rows": total_rows,
                "total_columns": len(headers)
            }
            
        elif file_extension == '.json':
            # Read JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list) and len(data) > 0:
                # Array of objects
                headers = list(data[0].keys()) if data else []
                sample_data = data[:5]
                total_rows = len(data)
                
                return {
                    "file_type": "json",
                    "headers": headers,
                    "sample_data": sample_data,
                    "total_rows": total_rows,
                    "total_columns": len(headers)
                }
            else:
                # Single object or other structure
                headers = list(data.keys()) if isinstance(data, dict) else []
                return {
                    "file_type": "json",
                    "headers": headers,
                    "sample_data": [data] if isinstance(data, dict) else data,
                    "total_rows": 1 if isinstance(data, dict) else len(data) if isinstance(data, list) else 1,
                    "total_columns": len(headers)
                }
        else:
            raise HTTPException(400, f"Unsupported file format: {file_extension}")
            
    except Exception as e:
        raise HTTPException(500, f"Error reading dataset file: {str(e)}")

@router.get("/datasets/{dataset_id}/info")
def get_dataset_info(dataset_id: int, session=Depends(get_session)):
    """
    Get dataset information including row count for sampling configuration
    """
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    
    if not dataset.file_path:
        raise HTTPException(400, "Dataset has no file path")
    
    # Construct the full path to the dataset file
    try:
        file_path = validate_dataset_file(dataset.file_path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    
    try:
        file_extension = file_path.suffix.lower()
        
        if file_extension == '.csv':
            # Read CSV file to get row count
            df = pd.read_csv(file_path)
            headers = df.columns.tolist()
            total_rows = len(df)
            
            return {
                "id": dataset.id,
                "name": dataset.name,
                "description": dataset.description,
                "file_type": "csv",
                "headers": headers,
                "total_rows": total_rows,
                "total_columns": len(headers)
            }
            
        elif file_extension == '.json':
            # Read JSON file to get row count
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                headers = list(data[0].keys()) if data else []
                total_rows = len(data)
                
                return {
                    "id": dataset.id,
                    "name": dataset.name,
                    "description": dataset.description,
                    "file_type": "json",
                    "headers": headers,
                    "total_rows": total_rows,
                    "total_columns": len(headers)
                }
            else:
                # Single object
                headers = list(data.keys()) if isinstance(data, dict) else []
                return {
                    "id": dataset.id,
                    "name": dataset.name,
                    "description": dataset.description,
                    "file_type": "json",
                    "headers": headers,
                    "total_rows": 1,
                    "total_columns": len(headers)
                }
        else:
            raise HTTPException(400, f"Unsupported file format: {file_extension}")
            
    except Exception as e:
        raise HTTPException(500, f"Error reading dataset file: {str(e)}")

@router.delete("/datasets/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: int, session=Depends(get_session)):
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    # Remove the file from the filesystem
    file_path = get_dataset_file_path(dataset.file_path)

    if file_path.exists():
        os.remove(file_path)

    session.delete(dataset)
    session.commit()
    return {"message": "Dataset deleted successfully"}