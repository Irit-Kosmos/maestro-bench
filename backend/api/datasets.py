from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from db import get_session
from models import Dataset

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

@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: int, session=Depends(get_session)):
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    
    session.delete(dataset)
    session.commit()
    
    return {"message": "Dataset deleted successfully"}
