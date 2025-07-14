from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session
import json
from db import get_session
from models import (
    Experiment, ExperimentAgentConfig, Dataset, Agent, PromptVersion, Model, 
    AgentTeam, ExperimentExecution, AgentExecutionSnapshot
)
from schemas.experiments import ExperimentCreate, ExperimentResponse, ExperimentUpdate, ExperimentAgentConfigResponse, DatasetResponse
from async_jobs import task_runner
from typing import List

router = APIRouter(tags=["experiments"])

@router.get("/experiments", response_model=List[ExperimentResponse])
def list_experiments(session: Session = Depends(get_session)):
    """Get all experiments"""
    experiments = session.exec(select(Experiment).order_by(Experiment.created_at.desc())).all()
    result = []
    for exp in experiments:
        # Fetch related data
        dataset = session.get(Dataset, exp.dataset_id) if exp.dataset_id else None
        agent_configs = session.exec(select(ExperimentAgentConfig).where(ExperimentAgentConfig.experiment_id == exp.id)).all()
        
        exp_response = ExperimentResponse(
            id=exp.id,
            name=exp.name,
            description=exp.description,
            dataset_id=exp.dataset_id,
            status=exp.status,
            created_at=exp.created_at,
            completed_at=exp.completed_at,
            sampling_type=exp.sampling_type,
            sampling_size=exp.sampling_size,
            sampling_start_row=exp.sampling_start_row,
            sampling_end_row=exp.sampling_end_row,
            dataset=DatasetResponse(
                id=dataset.id,
                name=dataset.name,
                description=dataset.description,
                file_path=dataset.file_path,
                created_at=dataset.created_at
            ) if dataset else None,
            experiment_configs=[]  # We'll populate this if needed
        )
        result.append(exp_response)
    return result

@router.post("/experiments", response_model=ExperimentResponse, status_code=201)
def create_experiment(exp_data: ExperimentCreate, session: Session = Depends(get_session)):
    """Create a new experiment with individual agent configurations and automatically start it"""
    
    # Create the base experiment
    experiment = Experiment(
        name=exp_data.name,
        description=exp_data.description,
        dataset_id=exp_data.dataset_id,
        sampling_type=exp_data.sampling_type,
        sampling_size=exp_data.sampling_size,
        sampling_start_row=exp_data.sampling_start_row,
        sampling_end_row=exp_data.sampling_end_row,
        column_mappings=json.dumps(exp_data.column_mappings) if exp_data.column_mappings else None
    )
    session.add(experiment)
    session.commit()
    session.refresh(experiment)
    
    # Create individual agent configurations only for explicitly configured and active agents
    execution_order = 1
    if exp_data.agent_teams and exp_data.agent_configurations:
        for team_id_str in exp_data.agent_teams:
            team_id = int(team_id_str)
            
            # Get all agents in this team
            agents = session.exec(select(Agent).where(Agent.team_id == team_id)).all()
            
            for agent in agents:
                # Only process agents that have explicit configurations
                agent_config = exp_data.agent_configurations.get(str(agent.id))
                if not agent_config:
                    continue
                
                # Skip inactive agents - only create configs for active agents
                if not agent_config.get('is_active', True):
                    print(f"Skipping inactive agent {agent.id} ({agent.name})")
                    continue
                
                # Determine prompt version (custom or default)
                prompt_version_id = agent_config.get('prompt_version_id') or agent.default_prompt_version_id
                if not prompt_version_id:
                    # If no prompt version specified and no default, skip this agent
                    print(f"Warning: Agent {agent.id} ({agent.name}) has no prompt version configured, skipping")
                    continue
                
                # Determine model (custom or default)
                model_id = agent_config.get('model_id') or agent.default_model_id
                if not model_id:
                    # If no model specified and no default, skip this agent
                    print(f"Warning: Agent {agent.id} ({agent.name}) has no model configured, skipping")
                    continue
                
                # Create experiment agent config
                exp_agent_config = ExperimentAgentConfig(
                    experiment_id=experiment.id,
                    agent_id=agent.id,
                    prompt_version_id=prompt_version_id,
                    model_id=model_id,
                    temperature=agent_config.get('temperature'),
                    max_tokens=agent_config.get('max_tokens'),
                    execution_order=execution_order,
                    is_active=True  # Only active agents reach this point
                )
                
                session.add(exp_agent_config)
                execution_order += 1
    
    session.commit()
    
    # Automatically start the experiment using async processing
    try:
        success = task_runner.start_experiment(experiment.id)
        if success:
            print(f"[API] Experiment {experiment.id} started with async processor")
        else:
            print(f"[API] Failed to start experiment {experiment.id}")
    except Exception as e:
        print(f"[API] Failed to start experiment {experiment.id}: {str(e)}")
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
        sampling_type=experiment.sampling_type,
        sampling_size=experiment.sampling_size,
        sampling_start_row=experiment.sampling_start_row,
        sampling_end_row=experiment.sampling_end_row,
        dataset=DatasetResponse(
            id=dataset.id,
            name=dataset.name,
            description=dataset.description,
            file_path=dataset.file_path,
            created_at=dataset.created_at
        ) if dataset else None,
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
    agent_configs = session.exec(select(ExperimentAgentConfig).where(ExperimentAgentConfig.experiment_id == exp_id)).all()
    
    return ExperimentResponse(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description,
        dataset_id=experiment.dataset_id,
        status=experiment.status,
        created_at=experiment.created_at,
        completed_at=experiment.completed_at,
        sampling_type=experiment.sampling_type,
        sampling_size=experiment.sampling_size,
        sampling_start_row=experiment.sampling_start_row,
        sampling_end_row=experiment.sampling_end_row,
        dataset=DatasetResponse(
            id=dataset.id,
            name=dataset.name,
            description=dataset.description,
            file_path=dataset.file_path,
            created_at=dataset.created_at
        ) if dataset else None,
        experiment_configs=[
            ExperimentAgentConfigResponse(
                id=config.id,
                experiment_id=config.experiment_id,
                agent_id=config.agent_id,
                prompt_version_id=config.prompt_version_id,
                model_id=config.model_id,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                execution_order=config.execution_order,
                is_active=config.is_active,
                created_at=config.created_at
            ) for config in agent_configs
        ]
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
        sampling_type=experiment.sampling_type,
        sampling_size=experiment.sampling_size,
        sampling_start_row=experiment.sampling_start_row,
        sampling_end_row=experiment.sampling_end_row,
        dataset=DatasetResponse(
            id=dataset.id,
            name=dataset.name,
            description=dataset.description,
            file_path=dataset.file_path,
            created_at=dataset.created_at
        ) if dataset else None,
        experiment_configs=[]
    )

@router.delete("/experiments/{exp_id}")
def delete_experiment(exp_id: int, session: Session = Depends(get_session)):
    """Delete an experiment and all its configurations"""
    experiment = session.get(Experiment, exp_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Delete all experiment executions and their related data first
    executions = session.exec(select(ExperimentExecution).where(ExperimentExecution.experiment_id == exp_id)).all()
    for execution in executions:
        # Delete all agent execution snapshots for this execution
        agent_snapshots = session.exec(select(AgentExecutionSnapshot).where(AgentExecutionSnapshot.execution_id == execution.id)).all()
        for snapshot in agent_snapshots:
            session.delete(snapshot)
        
        # Delete the execution itself
        session.delete(execution)
    
    # Delete all experiment agent configurations
    agent_configs = session.exec(select(ExperimentAgentConfig).where(ExperimentAgentConfig.experiment_id == exp_id)).all()
    for config in agent_configs:
        session.delete(config)
    
    # Delete the experiment
    session.delete(experiment)
    session.commit()
    
    return {"message": "Experiment deleted successfully"}

@router.get("/experiments/{experiment_id}/status")
def get_experiment_status(experiment_id: int):
    """Get the current processing status of an experiment"""
    task_status = task_runner.get_task_status(experiment_id)
    return {
        "experiment_id": experiment_id,
        "task_status": task_status
    }

@router.post("/experiments/{experiment_id}/cancel")
def cancel_experiment(experiment_id: int):
    """Cancel a running experiment"""
    success = task_runner.cancel_experiment(experiment_id)
    return {
        "experiment_id": experiment_id,
        "cancelled": success
    }

@router.post("/experiments/{experiment_id}/rerun")
def rerun_experiment(experiment_id: int, session: Session = Depends(get_session)):
    """Re-run an experiment with the same configuration by creating a new execution"""
    experiment = session.get(Experiment, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Check if experiment has any agent configurations
    agent_configs = session.exec(
        select(ExperimentAgentConfig).where(ExperimentAgentConfig.experiment_id == experiment_id)
    ).all()
    
    if not agent_configs:
        raise HTTPException(status_code=400, detail="Experiment has no agent configurations")
    
    # Start the experiment using the async task runner
    # This will create a new execution snapshot and run the experiment
    try:
        success = task_runner.start_experiment(experiment_id)
        if success:
            print(f"[API] Re-run started for experiment {experiment_id}")
            return {
                "experiment_id": experiment_id,
                "message": "Experiment re-run started successfully",
                "status": "started"
            }
        else:
            print(f"[API] Failed to start re-run for experiment {experiment_id}")
            raise HTTPException(status_code=500, detail="Failed to start experiment re-run")
    except Exception as e:
        print(f"[API] Failed to start re-run for experiment {experiment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start experiment re-run: {str(e)}")
