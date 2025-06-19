from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session
from db import get_session
from models import (
    Experiment, Dataset, ExperimentExecution, AgentExecutionConfig
)
from schemas.experiment_executions import (
    ExperimentExecutionResponse, ExperimentExecutionCreate, ExperimentExecutionUpdate,
    AgentExecutionConfigResponse, ExperimentTrace
)
from typing import List
import json
import os
from datetime import datetime

router = APIRouter(tags=["experiment-executions"])


@router.get("/experiments/{experiment_id}/executions", response_model=List[ExperimentExecutionResponse])
def get_experiment_executions(experiment_id: int, session: Session = Depends(get_session)):
    """Get all executions for a specific experiment"""
    executions = session.exec(
        select(ExperimentExecution).where(ExperimentExecution.experiment_id == experiment_id)
    ).all()
    
    result = []
    for execution in executions:
        # Get agent execution configs
        agent_configs = session.exec(
            select(AgentExecutionConfig).where(
                AgentExecutionConfig.experiment_execution_id == execution.id
            )
        ).all()
        
        agent_config_responses = [
            AgentExecutionConfigResponse(
                id=config.id,
                agent_id=config.agent_id,
                agent_name_snapshot=config.agent_name_snapshot,
                agent_team_id_snapshot=config.agent_team_id_snapshot,
                agent_team_name_snapshot=config.agent_team_name_snapshot,
                final_system_prompt=config.final_system_prompt,
                final_user_prompt=config.final_user_prompt,
                final_variables=config.final_variables,
                created_at=config.created_at
            ) for config in agent_configs
        ]
        
        result.append(ExperimentExecutionResponse(
            id=execution.id,
            experiment_id=execution.experiment_id,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            status=execution.status,
            dataset_snapshot=execution.dataset_snapshot,
            results_file_path=execution.results_file_path,
            agent_executions=agent_config_responses
        ))
    
    return result


@router.get("/executions/{execution_id}", response_model=ExperimentExecutionResponse)
def get_execution_details(execution_id: int, session: Session = Depends(get_session)):
    """Get detailed information about a specific execution"""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    # Get agent execution configs
    agent_configs = session.exec(
        select(AgentExecutionConfig).where(
            AgentExecutionConfig.experiment_execution_id == execution_id
        )
    ).all()
    
    agent_config_responses = [
        AgentExecutionConfigResponse(
            id=config.id,
            agent_id=config.agent_id,
            agent_name_snapshot=config.agent_name_snapshot,
            agent_team_id_snapshot=config.agent_team_id_snapshot,
            agent_team_name_snapshot=config.agent_team_name_snapshot,
            final_system_prompt=config.final_system_prompt,
            final_user_prompt=config.final_user_prompt,
            final_variables=config.final_variables,
            created_at=config.created_at
        ) for config in agent_configs
    ]
    
    return ExperimentExecutionResponse(
        id=execution.id,
        experiment_id=execution.experiment_id,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        status=execution.status,
        dataset_snapshot=execution.dataset_snapshot,
        results_file_path=execution.results_file_path,
        agent_executions=agent_config_responses
    )


@router.get("/executions/{execution_id}/trace", response_model=ExperimentTrace)
def get_execution_trace(execution_id: int, session: Session = Depends(get_session)):
    """Get complete scientific trace of an execution - the gold standard for reproducibility"""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    # Get experiment and dataset info
    experiment = session.get(Experiment, execution.experiment_id)
    dataset = session.get(Dataset, experiment.dataset_id)
    
    # Get agent execution configs
    agent_configs = session.exec(
        select(AgentExecutionConfig).where(
            AgentExecutionConfig.experiment_execution_id == execution_id
        )
    ).all()
    
    agent_config_responses = [
        AgentExecutionConfigResponse(
            id=config.id,
            agent_id=config.agent_id,
            agent_name_snapshot=config.agent_name_snapshot,
            agent_team_id_snapshot=config.agent_team_id_snapshot,
            agent_team_name_snapshot=config.agent_team_name_snapshot,
            final_system_prompt=config.final_system_prompt,
            final_user_prompt=config.final_user_prompt,
            final_variables=config.final_variables,
            created_at=config.created_at
        ) for config in agent_configs
    ]
    
    execution_response = ExperimentExecutionResponse(
        id=execution.id,
        experiment_id=execution.experiment_id,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        status=execution.status,
        dataset_snapshot=execution.dataset_snapshot,
        results_file_path=execution.results_file_path,
        agent_executions=agent_config_responses
    )
    
    # Load results summary from file if available
    results_summary = {}
    if execution.results_file_path and os.path.exists(execution.results_file_path):
        try:
            with open(execution.results_file_path, 'r') as f:
                results_data = json.load(f)
                results_summary = results_data.get('metadata', {})
        except Exception as e:
            print(f"Warning: Could not load results file: {e}")
    
    return ExperimentTrace(
        execution=execution_response,
        agent_configs=agent_config_responses,
        experiment_metadata={
            "id": experiment.id,
            "name": experiment.name,
            "description": experiment.description,
            "created_at": experiment.created_at.isoformat(),
            "dataset_id": experiment.dataset_id
        },
        dataset_metadata=json.loads(execution.dataset_snapshot),
        results_summary=results_summary
    )


@router.put("/executions/{execution_id}", response_model=ExperimentExecutionResponse)
def update_execution(
    execution_id: int, 
    update_data: ExperimentExecutionUpdate, 
    session: Session = Depends(get_session)
):
    """Update execution details - mainly for MAESTRO to report completion"""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(execution, field, value)
    
    session.add(execution)
    session.commit()
    session.refresh(execution)
    
    # Return updated execution with agent configs
    agent_configs = session.exec(
        select(AgentExecutionConfig).where(
            AgentExecutionConfig.experiment_execution_id == execution_id
        )
    ).all()
    
    agent_config_responses = [
        AgentExecutionConfigResponse(
            id=config.id,
            agent_id=config.agent_id,
            agent_name_snapshot=config.agent_name_snapshot,
            agent_team_id_snapshot=config.agent_team_id_snapshot,
            agent_team_name_snapshot=config.agent_team_name_snapshot,
            final_system_prompt=config.final_system_prompt,
            final_user_prompt=config.final_user_prompt,
            final_variables=config.final_variables,
            created_at=config.created_at
        ) for config in agent_configs
    ]
    
    return ExperimentExecutionResponse(
        id=execution.id,
        experiment_id=execution.experiment_id,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        status=execution.status,
        dataset_snapshot=execution.dataset_snapshot,
        results_file_path=execution.results_file_path,
        agent_executions=agent_config_responses
    )
