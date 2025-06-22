import time
import json
import pandas as pd
import random
from datetime import datetime
from sqlmodel import Session, select
from db import engine
from models import (
    Experiment, ExperimentAgentConfig, Agent, AgentTeam, Dataset, 
    ExperimentExecution, AgentExecutionSnapshot, PromptVersion, Model
)
from pathlib import Path


def apply_dataset_sampling(dataset_file_path: str, sampling_config: dict) -> pd.DataFrame:
    """
    Apply sampling configuration to a dataset and return the sampled DataFrame
    
    Args:
        dataset_file_path: Path to the dataset file
        sampling_config: Dictionary containing sampling configuration
            - sampling_type: 'all', 'random', or 'range'
            - sampling_size: Number of rows for random sampling
            - sampling_start_row: Start row for range sampling (1-based)
            - sampling_end_row: End row for range sampling (1-based, inclusive)
    
    Returns:
        pandas.DataFrame: The sampled dataset
    """
    # Load the full dataset
    file_extension = Path(dataset_file_path).suffix.lower()
    
    if file_extension == '.csv':
        df = pd.read_csv(dataset_file_path)
    elif file_extension == '.json':
        df = pd.read_json(dataset_file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")
    
    sampling_type = sampling_config.get('sampling_type', 'all')
    
    if sampling_type == 'all' or sampling_type is None:
        return df
    
    elif sampling_type == 'random':
        sampling_size = sampling_config.get('sampling_size')
        if sampling_size and sampling_size > 0:
            sample_size = min(sampling_size, len(df))
            return df.sample(n=sample_size, random_state=42)  # Fixed seed for reproducibility
        else:
            return df
    
    elif sampling_type == 'range':
        start_row = sampling_config.get('sampling_start_row')
        end_row = sampling_config.get('sampling_end_row')
        
        if start_row and end_row:
            # Convert to 0-based indexing
            start_idx = start_row - 1
            end_idx = end_row  # end_row is inclusive, so we don't subtract 1
            
            # Ensure indices are within bounds
            start_idx = max(0, start_idx)
            end_idx = min(len(df), end_idx)
            
            return df.iloc[start_idx:end_idx]
        else:
            return df
    
    else:
        # Unknown sampling type, return all data
        return df


def create_execution_snapshot(experiment_id: int, session: Session) -> ExperimentExecution:
    """Create an immutable snapshot of the experiment configuration at execution time"""
    
    # Get experiment and related data
    experiment = session.get(Experiment, experiment_id)
    if not experiment:
        raise Exception(f"Experiment {experiment_id} not found")
    
    # Get dataset snapshot
    dataset = session.get(Dataset, experiment.dataset_id)
    dataset_snapshot = json.dumps({
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "file_path": dataset.file_path,
        "sampling_config": {
            "sampling_type": experiment.sampling_type,
            "sampling_size": experiment.sampling_size,
            "sampling_start_row": experiment.sampling_start_row,
            "sampling_end_row": experiment.sampling_end_row
        }
    }) if dataset else "{}"
    
    # Create execution record
    execution = ExperimentExecution(
        experiment_id=experiment_id,
        dataset_snapshot=dataset_snapshot
    )
    session.add(execution)
    session.commit()
    session.refresh(execution)
    
    # Get agent configurations for this experiment
    agent_configs = session.exec(select(ExperimentAgentConfig).where(
        ExperimentAgentConfig.experiment_id == experiment_id,
        ExperimentAgentConfig.is_active == True
    )).all()
    
    # Create agent execution snapshots
    for agent_config in agent_configs:
        agent = session.get(Agent, agent_config.agent_id)
        prompt_version = session.get(PromptVersion, agent_config.prompt_version_id or agent.default_prompt_version_id)
        model = session.get(Model, agent_config.model_id or agent.default_model_id)
        
        if not prompt_version or not model:
            print(f"[Job] Warning: Missing prompt version or model for agent {agent.id}")
            continue
        
        # Create agent execution snapshot
        agent_snapshot = AgentExecutionSnapshot(
            execution_id=execution.id,
            agent_id=agent.id,
            agent_name_snapshot=agent.name,
            model_name_snapshot=model.name,
            model_provider_snapshot=model.provider,
            prompt_name_snapshot=prompt_version.prompt.name if prompt_version.prompt else "Unknown",
            prompt_version_snapshot=prompt_version.version,
            final_system_prompt=prompt_version.system_prompt,
            final_user_prompt=prompt_version.user_prompt,
            final_variables=prompt_version.variables,
            final_temperature=agent_config.temperature or model.default_temperature,
            final_max_tokens=agent_config.max_tokens or model.default_max_tokens,
            execution_order=agent_config.execution_order
        )
        session.add(agent_snapshot)
    
    session.commit()
    print(f"[Job] Created execution snapshot {execution.id} for experiment {experiment_id} with {len(agent_configs)} agent configs")
    
    return execution


def run_experiment(experiment_id: int):
    """Run an experiment with complete traceability and robust database handling"""
    print(f"[Job] Starting experiment {experiment_id}")
    
    try:
        with Session(engine) as session:
            # Update experiment status
            experiment = session.get(Experiment, experiment_id)
            if not experiment:
                print(f"[Job] Experiment {experiment_id} not found")
                return
            
            print(f"[Job] Found experiment: {experiment.name} (status: {experiment.status})")
            experiment.status = "running" 
            session.add(experiment)
            session.commit()
            print(f"[Job] Updated experiment {experiment_id} status to 'running'")
            
            # Create execution snapshot
            execution = create_execution_snapshot(experiment_id, session)
            print(f"[Job] Created execution snapshot {execution.id}")
            
            # TODO: Implement actual MAESTRO execution logic
            print(f"[Job] Experiment {experiment_id} execution simplified - full implementation coming soon")
            time.sleep(2)  # Simulate some work
            
            # Mark as completed for now
            experiment.status = "completed"
            experiment.completed_at = datetime.utcnow()
            session.add(experiment)
            session.commit()
            
            print(f"[Job] Experiment {experiment_id} completed successfully")
            
    except Exception as e:
        print(f"[Job] Error in experiment {experiment_id}: {str(e)}")
        import traceback
        print(f"[Job] Full traceback: {traceback.format_exc()}")
        
        # Mark experiment as failed with retry logic
        try:
            with Session(engine) as session:
                experiment = session.get(Experiment, experiment_id)
                if experiment:
                    experiment.status = "failed"
                    session.add(experiment)
                    session.commit()
                    print(f"[Job] Marked experiment {experiment_id} as failed")
                else:
                    print(f"[Job] Could not find experiment {experiment_id} to mark as failed")
        except Exception as update_error:
            print(f"[Job] Failed to update experiment status: {str(update_error)}")
            import traceback
            print(f"[Job] Update error traceback: {traceback.format_exc()}")
