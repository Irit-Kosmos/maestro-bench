from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session
from rq import Queue
from redis import Redis
import json
from db import get_session
from models import Experiment, ExperimentConfig, Dataset, Agent
from schemas.experiments import ExperimentCreate, ExperimentResponse, ExperimentUpdate
from jobs import run_experiment
from typing import List

router = APIRouter(tags=["experiments"])

# Initialize Redis connection and queue
redis_conn = Redis.from_url("redis://localhost:6379/0")
queue = Queue("experiments", connection=redis_conn)

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
    """Create a new experiment with agent team configurations and automatically start it"""
    
    # Create the base experiment
    experiment = Experiment(
        name=exp_data.name,
        description=exp_data.description,
        dataset_id=exp_data.dataset_id,
        agent_configurations=json.dumps(exp_data.agent_configurations) if exp_data.agent_configurations else None
    )
    session.add(experiment)
    session.commit()
    session.refresh(experiment)
    
    # Create experiment configurations for each agent team
    experiment_configs = []
    if exp_data.agent_teams:
        for i, team_id_str in enumerate(exp_data.agent_teams):
            team_id = int(team_id_str)
            
            # Create experiment config for this team
            config = ExperimentConfig(
                experiment_id=experiment.id,
                agent_team_id=team_id,
                active=True,
                priority=i + 1  # Priority based on order
            )
            
            # Store custom agent configurations in the config if provided
            # Note: Individual agent configs are now stored on the experiment itself
            # This is just for team-level overrides if needed
            session.add(config)
            experiment_configs.append(config)
    
    session.commit()
    
    # Automatically queue the experiment job
    try:
        job = queue.enqueue(run_experiment, experiment.id)
        print(f"[API] Experiment {experiment.id} queued with job ID: {job.id}")
        print(f"[API] Agent configurations stored in experiment: {json.dumps(exp_data.agent_configurations, indent=2) if exp_data.agent_configurations else 'None'}")
    except Exception as e:
        print(f"[API] Failed to queue experiment {experiment.id}: {str(e)}")
        # Don't fail the creation, just log the error
    
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
