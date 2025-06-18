from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session
from db import get_session
from models import Experiment, ExperimentConfig, Dataset
from schemas.experiments import ExperimentCreate, ExperimentResponse, ExperimentUpdate
from typing import List

router = APIRouter(tags=["experiments"])

@router.get("/experiments", response_model=List[ExperimentResponse])
def list_experiments(session: Session = Depends(get_session)):
    """Get all experiments"""
    experiments = session.exec(select(Experiment)).all()
    result = []
    for exp in experiments:
        # Fetch related data
        dataset = session.get(Dataset, exp.dataset_id) if exp.dataset_id else None
        configs = session.exec(select(ExperimentConfig).where(ExperimentConfig.experiment_id == exp.id)).all()
        
        exp_response = ExperimentResponse(
            id=exp.id,
            name=exp.name,
            description=exp.description,
            dataset_id=exp.dataset_id,
            status=exp.status,
            created_at=exp.created_at,
            completed_at=exp.completed_at,
            dataset={
                "id": dataset.id,
                "name": dataset.name,
                "description": dataset.description,
                "file_path": dataset.file_path,
                "created_at": dataset.created_at
            } if dataset else None,
            experiment_configs=[]  # We'll populate this if needed
        )
        result.append(exp_response)
    return result

@router.post("/experiments", response_model=ExperimentResponse, status_code=201)
def create_experiment(exp_data: ExperimentCreate, session: Session = Depends(get_session)):
    """Create a new experiment"""
    experiment = Experiment(**exp_data.model_dump())
    session.add(experiment)
    session.commit()
    session.refresh(experiment)
    
    # Return the created experiment with related data
    dataset = session.get(Dataset, experiment.dataset_id)
    return ExperimentResponse(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description,
        dataset_id=experiment.dataset_id,
        status=experiment.status,
        created_at=experiment.created_at,
        completed_at=experiment.completed_at,
        dataset={
            "id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            "file_path": dataset.file_path,
            "created_at": dataset.created_at
        } if dataset else None,
        experiment_configs=[]
    )

@router.get("/experiments/{exp_id}", response_model=ExperimentResponse)
def get_experiment(exp_id: int, session: Session = Depends(get_session)):
    """Get a specific experiment with all its configurations"""
    experiment = session.get(Experiment, exp_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Fetch related data
    dataset = session.get(Dataset, experiment.dataset_id) if experiment.dataset_id else None
    configs = session.exec(select(ExperimentConfig).where(ExperimentConfig.experiment_id == exp_id)).all()
    
    return ExperimentResponse(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description,
        dataset_id=experiment.dataset_id,
        status=experiment.status,
        created_at=experiment.created_at,
        completed_at=experiment.completed_at,
        dataset={
            "id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            "file_path": dataset.file_path,
            "created_at": dataset.created_at
        } if dataset else None,
        experiment_configs=[]  # We'll populate this with proper serialization if needed
    )

@router.put("/experiments/{exp_id}", response_model=ExperimentResponse)
def update_experiment(exp_id: int, exp_update: ExperimentUpdate, session: Session = Depends(get_session)):
    """Update an experiment"""
    experiment = session.get(Experiment, exp_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    exp_data = exp_update.model_dump(exclude_unset=True)
    for field, value in exp_data.items():
        setattr(experiment, field, value)
    
    session.add(experiment)
    session.commit()
    session.refresh(experiment)
    
    # Return updated experiment with related data
    dataset = session.get(Dataset, experiment.dataset_id) if experiment.dataset_id else None
    return ExperimentResponse(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description,
        dataset_id=experiment.dataset_id,
        status=experiment.status,
        created_at=experiment.created_at,
        completed_at=experiment.completed_at,
        dataset={
            "id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            "file_path": dataset.file_path,
            "created_at": dataset.created_at
        } if dataset else None,
        experiment_configs=[]
    )

@router.delete("/experiments/{exp_id}")
def delete_experiment(exp_id: int, session: Session = Depends(get_session)):
    """Delete an experiment and all its configurations"""
    experiment = session.get(Experiment, exp_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Delete all experiment configurations first
    configs = session.exec(select(ExperimentConfig).where(ExperimentConfig.experiment_id == exp_id)).all()
    for config in configs:
        session.delete(config)
    
    # Delete the experiment
    session.delete(experiment)
    session.commit()
    
    return {"message": "Experiment deleted successfully"}
