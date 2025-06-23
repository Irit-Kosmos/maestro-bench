import time
import json
import pandas as pd
import requests
from datetime import datetime

from typing import Optional
from sqlmodel import Session, select

from db import engine
from models import (
    Experiment, ExperimentAgentConfig, Agent, AgentTeam, Dataset, 
    ExperimentExecution, AgentExecutionSnapshot, PromptVersion, Model
)
from pathlib import Path


# MAESTRO API Configuration
MAESTRO_API_BASE_URL = "http://localhost:8001"
MAESTRO_API_TIMEOUT = 300  # 5 minutes timeout for long-running experiments


def apply_column_mappings(dataset_row: dict, column_mappings_json: Optional[str]) -> dict:
    """
    Apply column mappings to transform dataset columns into expected prompt variables
    
    Args:
        dataset_row: A single row from the dataset as a dictionary
        column_mappings_json: JSON string containing column mapping configuration
    
    Returns:
        dict: Transformed data with mapped column names
    """
    if not column_mappings_json:
        # If no column mappings, return the original data
        return dataset_row.copy()
    
    try:
        column_mappings = json.loads(column_mappings_json)
        if not isinstance(column_mappings, list):
            # If column mappings is not a list, return original data
            return dataset_row.copy()
        
        # Apply the mappings
        mapped_data = {}
        for mapping in column_mappings:
            if isinstance(mapping, dict) and 'sourceColumn' in mapping and 'targetField' in mapping:
                source_column = mapping['sourceColumn']
                target_field = mapping['targetField']
                if source_column in dataset_row:
                    mapped_data[target_field] = dataset_row[source_column]

        return mapped_data
        
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"[Job] Error applying column mappings: {e}")
        # Return original data if mapping fails
        return dataset_row.copy()


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
    # Default folder is '../datasets', so we prepend it to the file path
    dataset_file_path = Path("../datasets") / dataset_file_path
    if not dataset_file_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_file_path}")
    file_extension = dataset_file_path.suffix.lower()
    
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
            
            # Get dataset and apply sampling
            dataset_snapshot = json.loads(execution.dataset_snapshot)
            dataset_file_path = dataset_snapshot.get("file_path")
            sampling_config = dataset_snapshot.get("sampling_config", {})
            
            if not dataset_file_path:
                raise Exception("Dataset file path not found in snapshot")
                
            print(f"[Job] Loading dataset from {dataset_file_path}")
            sampled_dataset = apply_dataset_sampling(dataset_file_path, sampling_config)
            print(f"[Job] Dataset loaded with {len(sampled_dataset)} rows after sampling")
            
            # Execute experiment using MAESTRO API
            results_summary = execute_maestro_experiment(execution, sampled_dataset, session)
            print(f"[Job] MAESTRO execution completed: {results_summary}")
            
            # Mark execution as completed
            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            session.add(execution)
            
            # Mark experiment as completed
            experiment.status = "completed"
            experiment.completed_at = datetime.utcnow()
            session.add(experiment)
            session.commit()
            
            print(f"[Job] Experiment {experiment_id} completed successfully")
            
    except Exception as e:
        print(f"[Job] Error in experiment {experiment_id}: {str(e)}")
        import traceback
        print(f"[Job] Full traceback: {traceback.format_exc()}")
        
        # Mark experiment and execution as failed with retry logic
        try:
            with Session(engine) as session:
                experiment = session.get(Experiment, experiment_id)
                if experiment:
                    experiment.status = "failed"
                    session.add(experiment)
                    
                    # Also mark any running executions as failed
                    executions = session.exec(
                        select(ExperimentExecution)
                        .where(
                            ExperimentExecution.experiment_id == experiment_id,
                            ExperimentExecution.status == "running"
                        )
                    ).all()
                    
                    for execution in executions:
                        execution.status = "failed"
                        execution.completed_at = datetime.utcnow()
                        session.add(execution)
                    
                    session.commit()
                    print(f"[Job] Marked experiment {experiment_id} and its executions as failed")
                else:
                    print(f"[Job] Could not find experiment {experiment_id} to mark as failed")
        except Exception as update_error:
            print(f"[Job] Failed to update experiment status: {str(update_error)}")
            import traceback
            print(f"[Job] Update error traceback: {traceback.format_exc()}")

def build_maestro_request_payload(execution: ExperimentExecution, dataset_row: dict, session: Session) -> dict:
    """
    Build the MAESTRO API request payload from execution snapshot and dataset row
    
    Args:
        execution: The experiment execution with snapshots
        dataset_row: A single row from the dataset as a dictionary
        session: Database session
    
    Returns:
        dict: The MAESTRO API request payload
    """
    # Get the experiment to access column mappings
    experiment = session.get(Experiment, execution.experiment_id)
    if not experiment:
        raise ValueError(f"Experiment {execution.experiment_id} not found")
    

    # Apply column mappings to transform dataset row into expected format
    data = apply_column_mappings(dataset_row, experiment.column_mappings)
    
    # Get agent snapshots ordered by execution order
    agent_snapshots = session.exec(
        select(AgentExecutionSnapshot)
        .where(AgentExecutionSnapshot.execution_id == execution.id)
        .order_by("execution_order")
    ).all()
    
    # Build agents configuration
    agents = []
    for snapshot in agent_snapshots:
        # Parse variables from JSON string
        variables = []
        if snapshot.final_variables:
            try:
                variables_data = json.loads(snapshot.final_variables)
                if isinstance(variables_data, list):
                    # Variables stored as array of variable names
                    variables = variables_data
                elif isinstance(variables_data, dict):
                    # Variables stored as dictionary - extract keys
                    variables = list(variables_data.keys())
                else:
                    variables = []
            except (json.JSONDecodeError, TypeError):
                variables = []
        
        agent_config = {
            "agent_team_name": snapshot.agent.team.name if snapshot.agent and snapshot.agent.team else "Unknown",
            "agent_name": snapshot.agent_name_snapshot,
            "system_prompt": snapshot.final_system_prompt,
            "user_prompt": snapshot.final_user_prompt,
            "variables": variables,
            "model": snapshot.model_name_snapshot,
            "temperature": snapshot.final_temperature if snapshot.final_temperature is not None else 0.0
        }
        
        # Add max_tokens if available
        if snapshot.final_max_tokens is not None:
            agent_config["max_tokens"] = snapshot.final_max_tokens
            
        agents.append(agent_config)
    
    # Build the complete request payload
    request_payload = {
        "data": data,
        "config": {
            "agents": agents
        }
    }
    
    return request_payload


def call_maestro_api(request_payload: dict) -> dict:
    """
    Call the MAESTRO API with the given payload
    
    Args:
        request_payload: The request payload to send to MAESTRO
        
    Returns:
        dict: The response from MAESTRO API
        
    Raises:
        requests.RequestException: If the API call fails
        ValueError: If the response is not valid JSON
    """
    url = f"{MAESTRO_API_BASE_URL}/api/flexible-agents"
    
    try:
        print(f"[Job] Calling MAESTRO API at {url}")
        response = requests.post(
            url,
            json=request_payload,
            headers={"Content-Type": "application/json"},
            timeout=MAESTRO_API_TIMEOUT
        )
        
        response.raise_for_status()  # Raises an HTTPError for bad responses
        
        result = response.json()
        print(f"[Job] MAESTRO API call successful")
        return result
        
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Cannot connect to MAESTRO API at {url}. Make sure MAESTRO is running on port 8001."
        print(f"[Job] {error_msg}")
        raise requests.RequestException(error_msg) from e
        
    except requests.exceptions.Timeout as e:
        error_msg = f"MAESTRO API call timed out after {MAESTRO_API_TIMEOUT} seconds"
        print(f"[Job] {error_msg}")
        raise requests.RequestException(error_msg) from e
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"MAESTRO API returned error status {response.status_code}: {response.text}"
        print(f"[Job] {error_msg}")
        raise requests.RequestException(error_msg) from e
        
    except json.JSONDecodeError as e:
        error_msg = f"MAESTRO API returned invalid JSON response: {response.text}"
        print(f"[Job] {error_msg}")
        raise ValueError(error_msg) from e


def process_maestro_results(execution: ExperimentExecution, maestro_results: list, session: Session) -> dict:
    """
    Process MAESTRO results and save them to disk
    
    Args:
        execution: The experiment execution
        maestro_results: List of results from MAESTRO API
        session: Database session
        
    Returns:
        dict: Summary of the results
    """
    # Create results directory if it doesn't exist
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    # Save detailed results to file
    results_file_path = results_dir / f"experiment_{execution.experiment_id}_execution_{execution.id}_results.json"
    
    # Build the complete results structure
    complete_results = {
        "execution_id": execution.id,
        "experiment_id": execution.experiment_id,
        "total_questions_processed": len(maestro_results),
        "processing_time_seconds": (datetime.utcnow() - execution.started_at).total_seconds(),
        "results": maestro_results,
        "configuration_used": {
            "execution_id": execution.id,
            "dataset_snapshot": json.loads(execution.dataset_snapshot),
            "agents": [
                {
                    "agent_id": snapshot.agent_id,
                    "agent_name": snapshot.agent_name_snapshot,
                    "model_name": snapshot.model_name_snapshot,
                    "model_provider": snapshot.model_provider_snapshot,
                    "prompt_name": snapshot.prompt_name_snapshot,
                    "prompt_version": snapshot.prompt_version_snapshot,
                    "system_prompt": snapshot.final_system_prompt,
                    "user_prompt": snapshot.final_user_prompt,
                    "variables": json.loads(snapshot.final_variables) if snapshot.final_variables else {},
                    "temperature": snapshot.final_temperature,
                    "max_tokens": snapshot.final_max_tokens,
                    "execution_order": snapshot.execution_order
                }
                for snapshot in session.exec(
                    select(AgentExecutionSnapshot)
                    .where(AgentExecutionSnapshot.execution_id == execution.id)
                    .order_by("execution_order")
                ).all()
            ]
        },
        "maestro_version": "1.0.0",
        "completed_at": datetime.utcnow().isoformat()
    }
    
    # Calculate summary statistics
    if maestro_results:
        # Extract scores if available (this depends on MAESTRO response format)
        scores = []
        for result in maestro_results:
            if isinstance(result, dict) and 'score' in result:
                if isinstance(result['score'], (int, float)):
                    scores.append(result['score'])
                elif isinstance(result['score'], list) and result['score']:
                    # If score is a probability distribution, use the expected value
                    expected_score = sum(i * prob for i, prob in enumerate(result['score']))
                    scores.append(expected_score)
        
        if scores:
            complete_results["average_score"] = sum(scores) / len(scores)
            complete_results["min_score"] = min(scores)
            complete_results["max_score"] = max(scores)
    
    # Save to file
    with open(results_file_path, 'w') as f:
        json.dump(complete_results, f, indent=2, default=str)
    
    print(f"[Job] Results saved to {results_file_path}")
    
    # Update execution record with results file path
    execution.results_file_path = str(results_file_path)
    session.add(execution)
    session.commit()
    
    # Return summary for immediate use
    summary = {
        "total_questions_processed": complete_results["total_questions_processed"],
        "processing_time_seconds": complete_results["processing_time_seconds"],
        "results_file_path": str(results_file_path)
    }
    
    if "average_score" in complete_results:
        summary["average_score"] = complete_results["average_score"]
    
    return summary


def execute_maestro_experiment(execution: ExperimentExecution, sampled_dataset: pd.DataFrame, session: Session) -> dict:
    """
    Execute the experiment using MAESTRO API for each row in the dataset
    
    Args:
        execution: The experiment execution with snapshots
        sampled_dataset: The sampled dataset to process
        session: Database session
        
    Returns:
        dict: Summary of the execution results
    """
    maestro_results = []
    total_rows = len(sampled_dataset)
    
    print(f"[Job] Starting MAESTRO execution for {total_rows} rows")
    
    for idx, (_, row) in enumerate(sampled_dataset.iterrows(), 1):
        try:
            print(f"[Job] Processing row {idx}/{total_rows}")
            
            # Convert row to dictionary
            row_dict = row.to_dict()
            
            # Build MAESTRO request payload
            request_payload = build_maestro_request_payload(execution, row_dict, session)
            
            # Call MAESTRO API
            maestro_response = call_maestro_api(request_payload)
            
            # Store the result with metadata
            result_entry = {
                "row_index": idx,
                "input_data": row_dict,
                "maestro_response": maestro_response,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            maestro_results.append(result_entry)
            
            # Brief pause between requests to avoid overwhelming the API
            time.sleep(0.1)
            
        except Exception as e:
            error_msg = f"Error processing row {idx}: {str(e)}"
            print(f"[Job] {error_msg}")
            
            # Store error in results
            error_entry = {
                "row_index": idx,
                "input_data": row.to_dict(),
                "error": error_msg,
                "processed_at": datetime.utcnow().isoformat()
            }
            maestro_results.append(error_entry)
            
            # Continue with next row rather than failing the entire experiment
            continue
    
    print(f"[Job] MAESTRO execution completed. Processed {len(maestro_results)} rows")
    
    # Process and save results
    results_summary = process_maestro_results(execution, maestro_results, session)
    
    return results_summary
