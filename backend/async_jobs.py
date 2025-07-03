import asyncio
import aiohttp
import json
import pandas as pd
from datetime import datetime
from typing import Optional, AsyncGenerator, List, Dict, Any
from sqlmodel import Session, select
from pathlib import Path

from db import engine
from models import (
    Experiment, ExperimentAgentConfig, Agent, AgentTeam, Dataset, 
    ExperimentExecution, AgentExecutionSnapshot, PromptVersion, Model
)
from dataset_utils import validate_dataset_file
from config import MAESTRO_API_BASE_URL

# Constants
MAESTRO_API_TIMEOUT = 300  # 5 minutes timeout


class AsyncExperimentProcessor:
    """Async experiment processor with memory-efficient chunked processing"""
    
    def __init__(self, chunk_size: int = 5, max_concurrent: int = 2):
        """
        Initialize the async processor with conservative memory settings
        
        Args:
            chunk_size: Number of rows to process in each chunk (reduced from 10 to 5)
            max_concurrent: Maximum concurrent API calls (reduced from 3 to 2)
        """
        self.chunk_size = chunk_size
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    async def run_experiment_async(self, experiment_id: int) -> None:
        """Run an experiment asynchronously with chunked processing"""
        print(f"[AsyncJob] Starting async experiment {experiment_id}")
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=MAESTRO_API_TIMEOUT),
                connector=aiohttp.TCPConnector(limit=self.max_concurrent)
            ) as session:
                with Session(engine) as db_session:
                    # Update experiment status
                    experiment = db_session.get(Experiment, experiment_id)
                    if not experiment:
                        print(f"[AsyncJob] Experiment {experiment_id} not found")
                        return
                    
                    print(f"[AsyncJob] Found experiment: {experiment.name}")
                    experiment.status = "running"
                    db_session.add(experiment)
                    db_session.commit()
                    
                    # Create execution snapshot
                    execution = self._create_execution_snapshot(experiment_id, db_session)
                    print(f"[AsyncJob] Created execution snapshot {execution.id}")
                    
                    # Process experiment in chunks
                    results_summary = await self._process_experiment_chunks(
                        execution, session, db_session
                    )
                    
                    # Mark as completed
                    execution.status = "completed"
                    execution.completed_at = datetime.utcnow()
                    experiment.status = "completed"
                    experiment.completed_at = datetime.utcnow()
                    
                    db_session.add(execution)
                    db_session.add(experiment)
                    db_session.commit()
                    
                    print(f"[AsyncJob] Experiment {experiment_id} completed: {results_summary}")
                    
        except Exception as e:
            print(f"[AsyncJob] Error in experiment {experiment_id}: {str(e)}")
            await self._mark_experiment_failed(experiment_id, str(e))
    
    async def _process_experiment_chunks(
        self, execution: ExperimentExecution, 
        session: aiohttp.ClientSession, 
        db_session: Session
    ) -> Dict[str, Any]:
        """Process experiment data in memory-efficient chunks"""
        
        # Get dataset configuration
        dataset_snapshot = json.loads(execution.dataset_snapshot)
        dataset_file_path = dataset_snapshot.get("file_path")
        sampling_config = dataset_snapshot.get("sampling_config", {})
        
        if not dataset_file_path:
            raise Exception("Dataset file path not found in snapshot")
        
        print(f"[AsyncJob] Processing dataset: {dataset_file_path}")
        
        # Process in chunks to avoid memory issues
        all_results = []
        total_processed = 0
        
        async for chunk_results, chunk_size in self._process_dataset_chunks(
            dataset_file_path, sampling_config, execution, session, db_session
        ):
            all_results.extend(chunk_results)
            total_processed += chunk_size
            print(f"[AsyncJob] Processed {total_processed} rows so far...")
            
            # Force garbage collection after each chunk
            import gc
            gc.collect()
        
        # Save final results
        results_summary = self._save_results(execution, all_results, db_session)
        return results_summary
    
    async def _process_dataset_chunks(
        self, dataset_file_path: str, sampling_config: Dict,
        execution: ExperimentExecution, session: aiohttp.ClientSession,
        db_session: Session
    ) -> AsyncGenerator[tuple, None]:
        """Generator that yields processed chunks of dataset"""
        
        # Read dataset in chunks to manage memory
        dataset_full_path = validate_dataset_file(dataset_file_path)
        file_extension = dataset_full_path.suffix.lower()
        
        # Apply sampling to get the range we need to process
        sampling_type = sampling_config.get('sampling_type', 'all')
        
        if sampling_type == 'all':
            chunk_iterator = self._read_csv_chunks(dataset_full_path)
        elif sampling_type == 'random':
            # For random sampling, we need to load the full dataset first
            # but we'll process it in chunks
            df = self._apply_sampling(dataset_full_path, sampling_config)
            chunk_iterator = self._dataframe_to_chunks(df)
        elif sampling_type == 'range':
            start_row = sampling_config.get('sampling_start_row', 1) - 1  # Convert to 0-based
            end_row = sampling_config.get('sampling_end_row')
            chunk_iterator = self._read_csv_range_chunks(dataset_full_path, start_row, end_row)
        else:
            chunk_iterator = self._read_csv_chunks(dataset_full_path)
        
        # Process each chunk
        chunk_number = 0
        async for chunk_df in chunk_iterator:
            chunk_number += 1
            print(f"[AsyncJob] Processing chunk {chunk_number} with {len(chunk_df)} rows")
            
            # Process this chunk concurrently
            chunk_results = await self._process_chunk_concurrent(
                chunk_df, execution, session, db_session, chunk_number
            )
            
            yield chunk_results, len(chunk_df)
    
    async def _read_csv_chunks(self, file_path: Path) -> AsyncGenerator[pd.DataFrame, None]:
        """Read CSV file in chunks"""
        try:
            for chunk in pd.read_csv(file_path, chunksize=self.chunk_size):
                yield chunk
        except Exception as e:
            print(f"[AsyncJob] Error reading CSV chunks: {e}")
            raise
    
    async def _read_csv_range_chunks(
        self, file_path: Path, start_row: int, end_row: Optional[int]
    ) -> AsyncGenerator[pd.DataFrame, None]:
        """Read specific range of CSV in chunks"""
        try:
            nrows = None if end_row is None else (end_row - start_row)
            if start_row > 0:
                skiprows = list(range(1, start_row + 1))
                for chunk in pd.read_csv(file_path, chunksize=self.chunk_size, skiprows=skiprows, nrows=nrows):
                    yield chunk
            else:
                for chunk in pd.read_csv(file_path, chunksize=self.chunk_size, nrows=nrows):
                    yield chunk
        except Exception as e:
            print(f"[AsyncJob] Error reading CSV range chunks: {e}")
            raise
    
    async def _dataframe_to_chunks(self, df: pd.DataFrame) -> AsyncGenerator[pd.DataFrame, None]:
        """Split dataframe into chunks"""
        for i in range(0, len(df), self.chunk_size):
            yield df.iloc[i:i + self.chunk_size]
    
    def _apply_sampling(self, dataset_file_path: Path, sampling_config: Dict) -> pd.DataFrame:
        """Apply sampling configuration to dataset"""
        file_extension = dataset_file_path.suffix.lower()
        
        if file_extension == '.csv':
            df = pd.read_csv(dataset_file_path)
        elif file_extension == '.json':
            df = pd.read_json(dataset_file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        sampling_type = sampling_config.get('sampling_type', 'all')
        
        if sampling_type == 'random':
            sampling_size = sampling_config.get('sampling_size')
            if sampling_size and sampling_size > 0:
                sample_size = min(sampling_size, len(df))
                return df.sample(n=sample_size, random_state=42) # Fixed seed for reproducibility
        
        return df
    
    async def _process_chunk_concurrent(
        self, chunk_df: pd.DataFrame, execution: ExperimentExecution,
        session: aiohttp.ClientSession, db_session: Session, chunk_number: int
    ) -> List[Dict[str, Any]]:
        """Process a chunk of data with concurrent API calls"""
        
        # Create tasks for concurrent processing
        tasks = []
        for idx, (_, row) in enumerate(chunk_df.iterrows()):
            task = self._process_single_row(
                row, idx + ((chunk_number - 1) * self.chunk_size) + 1,
                execution, session, db_session
            )
            tasks.append(task)
        
        # Process all rows in this chunk concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return successful results
        chunk_results = []
        for result in results:
            if isinstance(result, Exception):
                print(f"[AsyncJob] Row processing error: {result}")
                # Add error entry
                chunk_results.append({
                    "error": str(result),
                    "processed_at": datetime.utcnow().isoformat()
                })
            else:
                chunk_results.append(result)
        
        return chunk_results
    
    async def _process_single_row(
        self, row: pd.Series, row_index: int,
        execution: ExperimentExecution, session: aiohttp.ClientSession,
        db_session: Session
    ) -> Dict[str, Any]:
        """Process a single row asynchronously"""
        
        async with self.semaphore:  # Limit concurrent requests
            try:
                # Convert row to dictionary
                row_dict = row.to_dict()
                
                # Build request payload
                request_payload = self._build_maestro_request_payload(
                    execution, row_dict, db_session
                )
                
                # Make async API call
                maestro_response = await self._call_maestro_api_async(
                    session, request_payload
                )
                
                return {
                    "row_index": row_index,
                    "input_data": row_dict,
                    "maestro_response": maestro_response,
                    "processed_at": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                return {
                    "row_index": row_index,
                    "input_data": row.to_dict(),
                    "error": str(e),
                    "processed_at": datetime.utcnow().isoformat()
                }
    
    async def _call_maestro_api_async(
        self, session: aiohttp.ClientSession, request_payload: Dict
    ) -> Dict[str, Any]:
        """Make async call to MAESTRO API"""
        url = f"{MAESTRO_API_BASE_URL}/api/flexible-agents"
        
        try:
            async with session.post(
                url,
                json=request_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result
                
        except aiohttp.ClientError as e:
            error_msg = f"MAESTRO API error: {str(e)}"
            print(f"[AsyncJob] {error_msg}")
            raise Exception(error_msg) from e
    
    def _build_maestro_request_payload(
        self, execution: ExperimentExecution, dataset_row: Dict,
        db_session: Session
    ) -> Dict[str, Any]:
        """Build MAESTRO API request payload - same logic as sync version"""
        # Get the experiment to access column mappings
        experiment = db_session.get(Experiment, execution.experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {execution.experiment_id} not found")
        
        # Apply column mappings
        from experiment_utils import apply_column_mappings
        data = apply_column_mappings(dataset_row, experiment.column_mappings)
        
        # Get agent snapshots
        agent_snapshots = db_session.exec(
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
                        variables = variables_data
                    elif isinstance(variables_data, dict):
                        variables = list(variables_data.keys())
                except (json.JSONDecodeError, TypeError):
                    pass
            
            agent_config = {
                "agent_team_name": snapshot.agent.team.name if snapshot.agent and snapshot.agent.team else "Unknown",
                "agent_name": snapshot.agent_name_snapshot,
                "system_prompt": snapshot.final_system_prompt,
                "user_prompt": snapshot.final_user_prompt,
                "variables": variables,
                "model": snapshot.model_name_snapshot,
                "provider": snapshot.model_provider_snapshot,
                "temperature": snapshot.final_temperature if snapshot.final_temperature is not None else 0.0
            }
            
            if snapshot.final_max_tokens is not None:
                agent_config["max_tokens"] = snapshot.final_max_tokens
                
            agents.append(agent_config)
        
        return {
            "data": data,
            "config": {
                "agents": agents
            }
        }
    
    def _create_execution_snapshot(
        self, experiment_id: int, session: Session
    ) -> ExperimentExecution:
        """Create execution snapshot - reuse logic from experiment_utils"""
        from experiment_utils import create_execution_snapshot
        return create_execution_snapshot(experiment_id, session)
    
    def _save_results(
        self, execution: ExperimentExecution, results: List[Dict],
        db_session: Session
    ) -> Dict[str, Any]:
        """Save results to file - reuse logic from experiment_utils"""
        from experiment_utils import process_maestro_results
        return process_maestro_results(execution, results, db_session)
    
    async def _mark_experiment_failed(self, experiment_id: int, error_msg: str):
        """Mark experiment as failed"""
        try:
            with Session(engine) as db_session:
                experiment = db_session.get(Experiment, experiment_id)
                if experiment:
                    experiment.status = "failed"
                    db_session.add(experiment)
                    
                    # Mark any running executions as failed
                    executions = db_session.exec(
                        select(ExperimentExecution)
                        .where(
                            ExperimentExecution.experiment_id == experiment_id,
                            ExperimentExecution.status == "running"
                        )
                    ).all()
                    
                    for execution in executions:
                        execution.status = "failed"
                        execution.completed_at = datetime.utcnow()
                        db_session.add(execution)
                    
                    db_session.commit()
                    print(f"[AsyncJob] Marked experiment {experiment_id} as failed: {error_msg}")
        except Exception as e:
            print(f"[AsyncJob] Failed to mark experiment as failed: {e}")


# Global processor instance
async_processor = AsyncExperimentProcessor(chunk_size=5, max_concurrent=2)


async def run_experiment_async(experiment_id: int) -> None:
    """Main async function to run an experiment"""
    await async_processor.run_experiment_async(experiment_id)


# Background task runner
import threading
from typing import Optional

class BackgroundTaskRunner:
    """Manages background async tasks without RQ"""
    
    def __init__(self):
        self.running_tasks: Dict[int, asyncio.Task] = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.loop_thread: Optional[threading.Thread] = None
        self._start_event_loop()
    
    def _start_event_loop(self):
        """Start the event loop in a background thread"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
        
        # Wait for loop to start
        import time
        time.sleep(0.1)
    
    def start_experiment(self, experiment_id: int) -> bool:
        """Start an experiment in the background"""
        try:
            if not self.loop or self.loop.is_closed():
                self._start_event_loop()
            
            if not self.loop:
                print(f"[TaskRunner] Failed to start event loop for experiment {experiment_id}")
                return False
            
            # Cancel existing task if running
            if experiment_id in self.running_tasks:
                old_task = self.running_tasks[experiment_id]
                asyncio.run_coroutine_threadsafe(self._cancel_task(old_task), self.loop)
            
            # Create new task
            future = asyncio.run_coroutine_threadsafe(
                run_experiment_async(experiment_id), 
                self.loop
            )
            
            # Convert future to task for tracking
            task = asyncio.run_coroutine_threadsafe(
                self._track_future(future, experiment_id),
                self.loop
            )
            
            print(f"[TaskRunner] Started async experiment {experiment_id}")
            return True
            
        except Exception as e:
            print(f"[TaskRunner] Failed to start experiment {experiment_id}: {e}")
            return False
    
    async def _cancel_task(self, task):
        """Cancel a task safely"""
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    async def _track_future(self, future, experiment_id):
        """Track a future and clean up when done"""
        try:
            await asyncio.wrap_future(future)
        finally:
            self.running_tasks.pop(experiment_id, None)
    
    def get_task_status(self, experiment_id: int) -> str:
        """Get status of a running experiment task"""
        if experiment_id not in self.running_tasks:
            return "not_running"
        
        task = self.running_tasks[experiment_id]
        if task.done():
            if task.exception():
                return "failed"
            return "completed"
        return "running"
    
    def cancel_experiment(self, experiment_id: int) -> bool:
        """Cancel a running experiment"""
        if experiment_id in self.running_tasks and self.loop:
            task = self.running_tasks[experiment_id]
            asyncio.run_coroutine_threadsafe(self._cancel_task(task), self.loop)
            return True
        return False


# Global task runner instance
task_runner = BackgroundTaskRunner()
