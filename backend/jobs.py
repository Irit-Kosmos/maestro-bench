import time
import json
import os
from datetime import datetime
from typing import Dict, List, Any
from sqlmodel import Session, select
from db import engine
from models import (
    Experiment, ExperimentConfig, Agent, AgentTeam, Dataset, 
    ExperimentExecution, AgentExecutionConfig
)


def create_execution_snapshot(experiment_id: int, session: Session) -> ExperimentExecution:
    """Create an immutable snapshot of the experiment configuration at execution time"""
    
    # Get experiment and related data
    experiment = session.get(Experiment, experiment_id)
    if not experiment:
        raise Exception(f"Experiment {experiment_id} not found")
    
    # Get dataset snapshot
    dataset = session.get(Dataset, experiment.dataset_id)
    dataset_snapshot = {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "file_path": dataset.file_path,
        "created_at": dataset.created_at.isoformat(),
        "file_size_bytes": None,  # Will be filled when file is accessed
        "total_questions": None   # Will be filled when file is parsed
    }
    
    # Create execution record
    execution = ExperimentExecution(
        experiment_id=experiment_id,
        dataset_snapshot=json.dumps(dataset_snapshot)
    )
    
    session.add(execution)
    session.commit()
    session.refresh(execution)
    
    # Get agent execution configs for this execution
    configs = session.exec(select(ExperimentConfig).where(
        ExperimentConfig.experiment_id == experiment_id,
        ExperimentConfig.active == True
    )).all()
    
    # Load custom agent configurations from experiment
    custom_agent_configs = {}
    if experiment.agent_configurations:
        try:
            custom_agent_configs = json.loads(experiment.agent_configurations)
        except json.JSONDecodeError:
            print(f"[Job] Warning: Could not parse agent configurations for experiment {experiment_id}")
    
    for config in configs:
        # Get agent team and agents
        agent_team = session.get(AgentTeam, config.agent_team_id)
        agents = session.exec(select(Agent).where(Agent.team_id == config.agent_team_id)).all()
        
        for agent in agents:
            # Get custom configuration for this agent if available
            agent_custom_config = custom_agent_configs.get(str(agent.id), {})
            
            # Determine the final prompts and variables to use
            final_system_prompt = agent_custom_config.get('system_prompt') or agent.system_prompt
            final_user_prompt = agent_custom_config.get('user_prompt') or agent.user_prompt
            final_variables = agent_custom_config.get('variables') or agent.variables
            
            # Create snapshot of each agent's FINAL configuration used
            agent_exec_config = AgentExecutionConfig(
                experiment_execution_id=execution.id,
                agent_id=agent.id,
                agent_name_snapshot=agent.name,
                agent_team_id_snapshot=agent_team.id,
                agent_team_name_snapshot=agent_team.name,
                # Store the EXACT prompts and variables that will be used
                final_system_prompt=final_system_prompt,
                final_user_prompt=final_user_prompt,
                final_variables=final_variables
            )
            session.add(agent_exec_config)
    
    session.commit()
    return execution


def call_maestro_for_execution(execution: ExperimentExecution, session: Session) -> str:
    """Call MAESTRO system to process the experiment and return path to results file"""
    
    # Parse dataset snapshot
    dataset_info = json.loads(execution.dataset_snapshot)
    dataset_file_path = os.path.join("datasets", dataset_info["file_path"])
    
    # Get agent execution configs for this execution
    agent_configs = session.exec(select(AgentExecutionConfig).where(
        AgentExecutionConfig.experiment_execution_id == execution.id
    )).all()
    
    print(f"[Job] Calling MAESTRO with {len(agent_configs)} agent configurations")
    
    # Prepare MAESTRO configuration
    maestro_config = {
        "execution_id": execution.id,
        "dataset_path": dataset_file_path,
        "agents": []
    }
    
    for agent_config in agent_configs:
        # Build the configuration for each agent as MAESTRO expects it
        agent_for_maestro = {
            "agent_id": agent_config.agent_id,
            "agent_name": agent_config.agent_name_snapshot,
            "system_prompt": agent_config.final_system_prompt,
            "user_prompt": agent_config.final_user_prompt,
            "variables": json.loads(agent_config.final_variables or "{}"),
            "team_id": agent_config.agent_team_id_snapshot,
            "team_name": agent_config.agent_team_name_snapshot
        }
        maestro_config["agents"].append(agent_for_maestro)
    
    # TODO: Replace this simulation with actual MAESTRO call
    # result_file_path = maestro.run_experiment(maestro_config)
    
    # For now, simulate MAESTRO processing and create a mock results file
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)
    result_file_path = os.path.join(results_dir, f"experiment_{execution.id}_results.json")
    
    # Simulate MAESTRO results
    mock_results = {
        "execution_id": execution.id,
        "total_questions_processed": 100,  # Simulated
        "agents_used": len(agent_configs),
        "processing_time_seconds": 45.2,
        "average_score": 4.1,
        "results": [
            # MAESTRO would populate this with actual question-answer pairs
            {"question_id": "q1", "agent_response": "Simulated response 1", "score": 4.2},
            {"question_id": "q2", "agent_response": "Simulated response 2", "score": 3.8}
        ],
        "configuration_used": maestro_config,
        "metadata": {
            "maestro_version": "1.0.0",
            "llm_model": "gpt-4",
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    # Write results file
    with open(result_file_path, 'w') as f:
        json.dump(mock_results, f, indent=2)
    
    print(f"[Job] MAESTRO processing complete. Results saved to: {result_file_path}")
    return result_file_path


def run_experiment(experiment_id: int):
    """Enhanced experiment runner with complete traceability and MAESTRO integration"""
    print(f"[Job] Starting experiment {experiment_id} with full traceability")
    
    try:
        with Session(engine) as session:
            # Update experiment status
            experiment = session.get(Experiment, experiment_id)
            if not experiment:
                print(f"[Job] Error: Experiment {experiment_id} not found")
                return {"status": "failed", "error": "Experiment not found"}
            
            experiment.status = "running"
            session.add(experiment)
            session.commit()
            
            # Create execution snapshot
            print(f"[Job] Creating execution snapshot for experiment {experiment_id}")
            execution = create_execution_snapshot(experiment_id, session)
            
            # Call MAESTRO to process the experiment
            print(f"[Job] Calling MAESTRO for execution {execution.id}")
            results_file_path = call_maestro_for_execution(execution, session)
            
            # Load results to get summary metrics
            with open(results_file_path, 'r') as f:
                results_data = json.load(f)
            
            # Update execution with results
            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            execution.results_file_path = results_file_path
            
            session.add(execution)
            session.commit()
            
            # Update main experiment
            experiment.status = "completed"
            experiment.completed_at = datetime.utcnow()
            session.add(experiment)
            session.commit()
            
            print(f"[Job] Experiment {experiment_id} completed with execution {execution.id}")
            print(f"[Job] Results file: {results_file_path}")
            
            return {
                "status": "completed",
                "experiment_id": experiment_id,
                "execution_id": execution.id,
                "results_file_path": results_file_path
            }
            
    except Exception as e:
        print(f"[Job] Error processing experiment {experiment_id}: {str(e)}")
        
        # Try to update status to failed
        try:
            with Session(engine) as session:
                experiment = session.get(Experiment, experiment_id)
                if experiment:
                    experiment.status = "failed"
                    session.add(experiment)
                    session.commit()
        except Exception as update_error:
            print(f"[Job] Failed to update experiment status to failed: {update_error}")
        
        return {"status": "failed", "error": str(e)}
