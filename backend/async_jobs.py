"""
Async experiment processor.

Experiments are dispatched as native asyncio Tasks on uvicorn's event loop via
`asyncio.create_task()`.  No daemon threads, no secondary event loops.
"""

import asyncio
import aiohttp
import json
import pandas as pd
from datetime import datetime
from typing import Optional, AsyncGenerator, List, Dict, Any
from sqlmodel import Session

from db import engine
from tables import Experiment, ExperimentExecution, AgentExecutionSnapshot
from dataset_utils import validate_dataset_file
from config import MAESTRO_API_BASE_URL

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAESTRO_API_TIMEOUT = 300  # seconds


# ---------------------------------------------------------------------------
# Task registry — maps experiment_id → running asyncio.Task
# ---------------------------------------------------------------------------

_running_tasks: Dict[int, asyncio.Task] = {}


def start_experiment(experiment_id: int) -> bool:
    """
    Schedule an experiment run as a background asyncio Task.
    Must be called from within an async context (e.g. a FastAPI async route).
    Cancels any previously running task for the same experiment_id.
    """
    existing = _running_tasks.get(experiment_id)
    if existing and not existing.done():
        existing.cancel()

    task = asyncio.create_task(run_experiment_async(experiment_id))
    _running_tasks[experiment_id] = task
    task.add_done_callback(lambda _t: _running_tasks.pop(experiment_id, None))
    return True


def get_task_status(experiment_id: int) -> str:
    """Return the in-memory status of an experiment task."""
    task = _running_tasks.get(experiment_id)
    if task is None:
        return "not_running"
    if task.done():
        return "failed" if task.exception() else "completed"
    return "running"


def cancel_experiment(experiment_id: int) -> bool:
    """Cancel a running experiment task. Returns True if a task was found."""
    task = _running_tasks.get(experiment_id)
    if task and not task.done():
        task.cancel()
        return True
    return False


# ---------------------------------------------------------------------------
# Core experiment runner
# ---------------------------------------------------------------------------


async def run_experiment_async(experiment_id: int) -> None:
    """Top-level coroutine that runs an experiment end-to-end."""
    print(f"[AsyncJob] Starting experiment {experiment_id}")

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=MAESTRO_API_TIMEOUT),
            connector=aiohttp.TCPConnector(limit=_processor.max_concurrent),
        ) as http_session:
            with Session(engine) as db_session:
                experiment = db_session.get(Experiment, experiment_id)
                if not experiment:
                    print(f"[AsyncJob] Experiment {experiment_id} not found")
                    return

                print(f"[AsyncJob] Found experiment: {experiment.name}")
                experiment.status = "running"
                db_session.add(experiment)
                db_session.commit()

                execution = _processor.create_execution_snapshot(
                    experiment_id, db_session
                )
                print(f"[AsyncJob] Created execution snapshot {execution.id}")

                results_summary = await _processor.process_experiment_chunks(
                    execution, http_session, db_session
                )

                execution.status = "completed"
                execution.completed_at = datetime.utcnow()
                experiment.status = "completed"
                experiment.completed_at = datetime.utcnow()

                db_session.add(execution)
                db_session.add(experiment)
                db_session.commit()

                print(
                    f"[AsyncJob] Experiment {experiment_id} completed: {results_summary}"
                )

    except asyncio.CancelledError:
        print(f"[AsyncJob] Experiment {experiment_id} cancelled")
        await _mark_experiment_failed(experiment_id, "cancelled")
        raise

    except Exception as e:
        print(f"[AsyncJob] Error in experiment {experiment_id}: {e}")
        await _mark_experiment_failed(experiment_id, str(e))


async def _mark_experiment_failed(experiment_id: int, error_msg: str) -> None:
    """Mark experiment and any running executions as failed."""
    try:
        from sqlmodel import select

        with Session(engine) as db_session:
            experiment = db_session.get(Experiment, experiment_id)
            if experiment:
                experiment.status = "failed"
                db_session.add(experiment)

                running_executions = db_session.exec(
                    select(ExperimentExecution).where(
                        ExperimentExecution.experiment_id == experiment_id,
                        ExperimentExecution.status == "running",
                    )
                ).all()

                for exc in running_executions:
                    exc.status = "failed"
                    exc.completed_at = datetime.utcnow()
                    db_session.add(exc)

                db_session.commit()
                print(
                    f"[AsyncJob] Marked experiment {experiment_id} as failed: {error_msg}"
                )
    except Exception as e:
        print(f"[AsyncJob] Failed to mark experiment as failed: {e}")


# ---------------------------------------------------------------------------
# Chunked processor
# ---------------------------------------------------------------------------


class AsyncExperimentProcessor:
    """Async experiment processor with memory-efficient chunked processing."""

    def __init__(self, chunk_size: int = 5, max_concurrent: int = 2):
        self.chunk_size = chunk_size
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    # ------------------------------------------------------------------
    # Snapshot helpers — delegate to experiment_utils
    # ------------------------------------------------------------------

    def create_execution_snapshot(
        self, experiment_id: int, session: Session
    ) -> ExperimentExecution:
        from experiment_utils import create_execution_snapshot

        return create_execution_snapshot(experiment_id, session)

    def save_results(
        self, execution: ExperimentExecution, results: List[Dict], db_session: Session
    ) -> Dict[str, Any]:
        from experiment_utils import process_maestro_results

        return process_maestro_results(execution, results, db_session)

    # ------------------------------------------------------------------
    # Main chunk processing pipeline
    # ------------------------------------------------------------------

    async def process_experiment_chunks(
        self,
        execution: ExperimentExecution,
        http_session: aiohttp.ClientSession,
        db_session: Session,
    ) -> Dict[str, Any]:
        dataset_snapshot = json.loads(execution.dataset_snapshot)
        dataset_file_path = dataset_snapshot.get("file_path")
        sampling_config = dataset_snapshot.get("sampling_config", {})

        if not dataset_file_path:
            raise ValueError("Dataset file path not found in snapshot")

        print(f"[AsyncJob] Processing dataset: {dataset_file_path}")

        all_results: List[Dict] = []
        total_processed = 0

        async for chunk_results, chunk_size in self._process_dataset_chunks(
            dataset_file_path, sampling_config, execution, http_session, db_session
        ):
            all_results.extend(chunk_results)
            total_processed += chunk_size
            print(f"[AsyncJob] Processed {total_processed} rows so far...")

            import gc

            gc.collect()

        return self.save_results(execution, all_results, db_session)

    async def _process_dataset_chunks(
        self,
        dataset_file_path: str,
        sampling_config: Dict,
        execution: ExperimentExecution,
        http_session: aiohttp.ClientSession,
        db_session: Session,
    ) -> AsyncGenerator[tuple, None]:
        """Yield (chunk_results, chunk_size) for each processed chunk."""
        from experiment_utils import apply_dataset_sampling

        dataset_full_path = validate_dataset_file(dataset_file_path)
        sampling_type = sampling_config.get("sampling_type", "all")

        if sampling_type == "all":
            chunk_iterator = self._read_csv_chunks(dataset_full_path)
        elif sampling_type == "random":
            df = apply_dataset_sampling(dataset_file_path, sampling_config)
            chunk_iterator = self._dataframe_to_chunks(df)
        elif sampling_type == "range":
            start_row = sampling_config.get("sampling_start_row", 1) - 1
            end_row = sampling_config.get("sampling_end_row")
            chunk_iterator = self._read_csv_range_chunks(
                dataset_full_path, start_row, end_row
            )
        else:
            chunk_iterator = self._read_csv_chunks(dataset_full_path)

        chunk_number = 0
        async for chunk_df in chunk_iterator:
            chunk_number += 1
            print(
                f"[AsyncJob] Processing chunk {chunk_number} with {len(chunk_df)} rows"
            )
            chunk_results = await self._process_chunk_concurrent(
                chunk_df, execution, http_session, db_session, chunk_number
            )
            yield chunk_results, len(chunk_df)

    # ------------------------------------------------------------------
    # CSV reading helpers
    # ------------------------------------------------------------------

    async def _read_csv_chunks(
        self, file_path
    ) -> AsyncGenerator[pd.DataFrame, None]:
        try:
            for chunk in pd.read_csv(file_path, chunksize=self.chunk_size):
                yield chunk
        except Exception as e:
            print(f"[AsyncJob] Error reading CSV chunks: {e}")
            raise

    async def _read_csv_range_chunks(
        self, file_path, start_row: int, end_row: Optional[int]
    ) -> AsyncGenerator[pd.DataFrame, None]:
        try:
            nrows = None if end_row is None else (end_row - start_row)
            skiprows = list(range(1, start_row + 1)) if start_row > 0 else None
            for chunk in pd.read_csv(
                file_path,
                chunksize=self.chunk_size,
                skiprows=skiprows,
                nrows=nrows,
            ):
                yield chunk
        except Exception as e:
            print(f"[AsyncJob] Error reading CSV range chunks: {e}")
            raise

    async def _dataframe_to_chunks(
        self, df: pd.DataFrame
    ) -> AsyncGenerator[pd.DataFrame, None]:
        for i in range(0, len(df), self.chunk_size):
            yield df.iloc[i : i + self.chunk_size]

    # ------------------------------------------------------------------
    # Row-level concurrent processing
    # ------------------------------------------------------------------

    async def _process_chunk_concurrent(
        self,
        chunk_df: pd.DataFrame,
        execution: ExperimentExecution,
        http_session: aiohttp.ClientSession,
        db_session: Session,
        chunk_number: int,
    ) -> List[Dict[str, Any]]:
        tasks = [
            self._process_single_row(
                row,
                idx + ((chunk_number - 1) * self.chunk_size) + 1,
                execution,
                http_session,
                db_session,
            )
            for idx, (_, row) in enumerate(chunk_df.iterrows())
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        chunk_results = []
        for result in results:
            if isinstance(result, Exception):
                print(f"[AsyncJob] Row processing error: {result}")
                chunk_results.append(
                    {
                        "error": str(result),
                        "processed_at": datetime.utcnow().isoformat(),
                    }
                )
            else:
                chunk_results.append(result)

        return chunk_results

    async def _process_single_row(
        self,
        row: pd.Series,
        row_index: int,
        execution: ExperimentExecution,
        http_session: aiohttp.ClientSession,
        db_session: Session,
    ) -> Dict[str, Any]:
        async with self.semaphore:
            try:
                from experiment_utils import build_maestro_request_payload

                row_dict = row.to_dict()
                request_payload = build_maestro_request_payload(
                    execution, row_dict, db_session
                )
                maestro_response = await self._call_maestro_api(
                    http_session, request_payload
                )
                return {
                    "row_index": row_index,
                    "input_data": row_dict,
                    "maestro_response": maestro_response,
                    "processed_at": datetime.utcnow().isoformat(),
                }
            except Exception as e:
                return {
                    "row_index": row_index,
                    "input_data": row.to_dict(),
                    "error": str(e),
                    "processed_at": datetime.utcnow().isoformat(),
                }

    async def _call_maestro_api(
        self, http_session: aiohttp.ClientSession, request_payload: Dict
    ) -> Dict[str, Any]:
        url = f"{MAESTRO_API_BASE_URL}/api/flexible-agents"
        try:
            async with http_session.post(
                url,
                json=request_payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            raise RuntimeError(f"MAESTRO API error: {e}") from e


# Module-level processor instance
_processor = AsyncExperimentProcessor(chunk_size=5, max_concurrent=2)
