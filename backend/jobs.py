import time
import json
from datetime import datetime
from sqlmodel import Session, select
from db import engine
from models import (
    Experiment, ExperimentAgentConfig, Agent, AgentTeam, Dataset, 
    ExperimentExecution, AgentExecutionSnapshot, PromptVersion, Model
)


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
        "file_path": dataset.file_path
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
            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            session.add(execution)
            
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
