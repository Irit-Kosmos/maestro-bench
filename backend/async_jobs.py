"""
Async experiment processor.

Experiments are dispatched as native asyncio Tasks on uvicorn's event loop
and run through the core pipeline engine (LiteLLM + orchestrator).
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy import update
from sqlmodel import Session, col, select

import config
import event_bus
from core.orchestrator import AgentConfig, PipelineResult, run_pipeline
from dataset_utils import count_csv_rows, validate_dataset_file
from db import engine
from experiment_utils import (
    apply_dataset_sampling,
    build_agent_configs_from_snapshot,
    create_execution_snapshot,
    process_pipeline_results,
)
from schemas.events import RunEvent, RunState
from tables import Experiment, ExperimentExecution
from workspace_scope import scope_session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CHUNK_SIZE = 5
DEFAULT_MAX_CONCURRENT = 2

# ---------------------------------------------------------------------------
# Scheduler — at most N experiments run at once, the others wait their turn
# ---------------------------------------------------------------------------

# experiment_id → the asyncio.Task running it. An entry stays until the task is done.
_running_tasks: dict[int, asyncio.Task] = {}
_workspace_of_task: dict[int, int] = {}
# Experiments waiting for a free slot, oldest first: (experiment_id, workspace_id)
_queue: list[tuple[int, int]] = []


def _has_room(workspace_id: int) -> bool:
    """Whether another experiment of the workspace may start right now."""
    in_workspace = sum(1 for w in _workspace_of_task.values() if w == workspace_id)
    return (
        len(_running_tasks) < config.MAX_CONCURRENT_EXPERIMENTS
        and in_workspace < config.MAX_CONCURRENT_EXPERIMENTS_PER_WORKSPACE
    )


def _launch(experiment_id: int, workspace_id: int) -> None:
    task = asyncio.create_task(run_experiment_async(experiment_id))
    _running_tasks[experiment_id] = task
    _workspace_of_task[experiment_id] = workspace_id

    def _cleanup(finished: asyncio.Task, eid: int = experiment_id) -> None:
        # Only drop the entry if it still points at this task. A re-run may have
        # replaced it with a newer task, and a cancelled task's callback fires
        # late — without this check it would evict the live replacement.
        if _running_tasks.get(eid) is finished:
            _running_tasks.pop(eid, None)
            _workspace_of_task.pop(eid, None)
        _start_waiting()

    task.add_done_callback(_cleanup)


def _start_waiting() -> None:
    """Start the oldest waiting experiments that now have a slot.

    A workspace that is at its limit does not hold back the others: its
    experiments are skipped until one of its own runs ends.
    """
    for entry in list(_queue):
        if _has_room(entry[1]):
            _queue.remove(entry)
            _launch(*entry)


def start_experiment(experiment_id: int, workspace_id: int) -> str:
    """Run an experiment now, or queue it when the limits are reached.

    Returns "started" or "queued". Starting an experiment that is already running
    restarts it on the slot it holds; one that is already queued keeps its place.
    """
    existing = _running_tasks.get(experiment_id)
    if existing and not existing.done():
        existing.cancel()
        _launch(experiment_id, workspace_id)
        return "started"

    if any(queued_id == experiment_id for queued_id, _ in _queue):
        return "queued"

    if _has_room(workspace_id):
        _launch(experiment_id, workspace_id)
        return "started"

    _queue.append((experiment_id, workspace_id))
    _mark_queued(experiment_id)
    logger.info("Experiment %s queued", experiment_id)
    return "queued"


def cancel_experiment(experiment_id: int) -> bool:
    """Cancel a running experiment task, or take a waiting one out of the queue."""
    waiting = next((e for e in _queue if e[0] == experiment_id), None)
    if waiting is not None:
        _queue.remove(waiting)
        _close_run(experiment_id, "cancelled", "cancelled while queued")
        return True

    task = _running_tasks.get(experiment_id)
    if task and not task.done():
        task.cancel()
        return True
    return False


def _mark_queued(experiment_id: int) -> None:
    """Record that an experiment waits, and tell the clients."""
    try:
        with Session(engine) as db_session:
            experiment = db_session.get(Experiment, experiment_id)
            if not experiment:
                return
            scope_session(db_session, experiment.workspace_id)
            experiment.status = "queued"
            db_session.add(experiment)
            db_session.commit()
            state = RunState(
                experiment_id=experiment_id,
                batch_id=experiment.batch_id,
                status="queued",
            )
            workspace_id = experiment.workspace_id
        event_bus.publish(
            RunEvent(name="status", state=state, workspace_id=workspace_id)
        )
    except Exception:
        logger.exception("Failed to mark experiment %s as queued", experiment_id)


def reap_interrupted_runs() -> int:
    """Close the runs a restart cut short; returns how many experiments it closed.

    Runs only live in this process, so at startup none can still be going: every
    experiment left "running" or "queued" would stay that way forever. There must
    be a single backend process for this to hold.
    """
    with Session(engine) as db_session:
        db_session.execute(
            update(ExperimentExecution)
            .where(col(ExperimentExecution.status) == "running")
            .values(status="interrupted", completed_at=datetime.now(UTC))
        )
        result = db_session.execute(
            update(Experiment)
            .where(col(Experiment.status).in_(("running", "queued")))
            .values(status="interrupted")
        )
        db_session.commit()
        return result.rowcount


# ---------------------------------------------------------------------------
# Core experiment runner
# ---------------------------------------------------------------------------


async def run_experiment_async(experiment_id: int) -> None:
    """Top-level coroutine that runs an experiment end-to-end."""
    logger.info("Starting experiment %s", experiment_id)

    try:
        with Session(engine) as db_session:
            experiment = db_session.get(Experiment, experiment_id)
            if not experiment:
                logger.warning("Experiment %s not found", experiment_id)
                return

            # From here on the run only sees the experiment's own workspace
            scope_session(db_session, experiment.workspace_id)
            logger.info("Found experiment: %s", experiment.name)
            experiment.status = "running"
            db_session.add(experiment)
            db_session.commit()

            # Create immutable execution snapshot
            execution = create_execution_snapshot(experiment_id, db_session)
            logger.info("Created execution snapshot %s", execution.id)

            progress = _RunProgress(
                db_session, execution, experiment.batch_id, experiment.workspace_id
            )
            progress.announce("running")

            # Run the experiment pipeline
            processor = _ExperimentProcessor(
                progress,
                chunk_size=DEFAULT_CHUNK_SIZE,
                max_concurrent=DEFAULT_MAX_CONCURRENT,
            )
            results_summary = await processor.process_experiment(
                execution, db_session
            )

            execution.status = "completed"
            execution.completed_at = datetime.now(UTC)
            experiment.status = "completed"
            experiment.completed_at = datetime.now(UTC)

            db_session.add(execution)
            db_session.add(experiment)
            db_session.commit()
            progress.announce("completed")

            logger.info("Experiment %s completed: %s", experiment_id, results_summary)

    except asyncio.CancelledError:
        logger.info("Experiment %s cancelled", experiment_id)
        _close_run(experiment_id, "cancelled", "cancelled")
        raise

    except Exception as e:
        logger.exception("Error in experiment %s", experiment_id)
        _close_run(experiment_id, "failed", str(e))


def _close_run(experiment_id: int, status: str, reason: str) -> None:
    """Mark an experiment and its running executions as failed or cancelled."""
    try:
        with Session(engine) as db_session:
            experiment = db_session.get(Experiment, experiment_id)
            if not experiment:
                return
            scope_session(db_session, experiment.workspace_id)
            experiment.status = status
            db_session.add(experiment)

            running_executions = db_session.exec(
                select(ExperimentExecution).where(
                    ExperimentExecution.experiment_id == experiment_id,
                    ExperimentExecution.status == "running",
                )
            ).all()

            for exc in running_executions:
                exc.status = status
                exc.completed_at = datetime.now(UTC)
                db_session.add(exc)

            db_session.commit()
            logger.info("Marked experiment %s as %s: %s", experiment_id, status, reason)

            workspace_id = experiment.workspace_id
            states = [
                RunState.from_execution(exc, experiment.batch_id)
                for exc in running_executions
            ] or [
                RunState(
                    experiment_id=experiment_id,
                    batch_id=experiment.batch_id,
                    status=status,
                )
            ]
        for state in states:
            event_bus.publish(
                RunEvent(name="status", state=state, workspace_id=workspace_id)
            )
    except Exception:
        logger.exception("Failed to mark experiment %s as %s", experiment_id, status)


class _RunProgress:
    """Counts the rows of an execution as they finish and publishes the count."""

    def __init__(
        self,
        session: Session,
        execution: ExperimentExecution,
        batch_id: int | None,
        workspace_id: int,
    ):
        self._session = session
        self._execution = execution
        self._workspace_id = workspace_id
        self._state = RunState.from_execution(execution, batch_id)

    def start(self, total: int) -> None:
        self._state.rows_total = total
        self._save()

    def row_done(self, *, failed: bool) -> None:
        self._state.rows_done += 1
        self._state.rows_failed += int(failed)
        self._save()

    def announce(self, status: str) -> None:
        """Publish a status the caller has already committed."""
        self._state.status = status
        event_bus.publish(
            RunEvent(
                name="status",
                state=self._state.model_copy(),
                workspace_id=self._workspace_id,
            )
        )

    def _save(self) -> None:
        self._execution.rows_total = self._state.rows_total
        self._execution.rows_done = self._state.rows_done
        self._execution.rows_failed = self._state.rows_failed
        self._session.commit()
        event_bus.publish(
            RunEvent(
                name="progress",
                state=self._state.model_copy(),
                workspace_id=self._workspace_id,
            )
        )


# ---------------------------------------------------------------------------
# Experiment processor — uses core engine
# ---------------------------------------------------------------------------


class _ExperimentProcessor:
    """Processes experiments using the core pipeline engine."""

    def __init__(
        self,
        progress: _RunProgress,
        chunk_size: int = 5,
        max_concurrent: int = 2,
    ):
        self.progress = progress
        self.chunk_size = chunk_size
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def process_experiment(
        self,
        execution: ExperimentExecution,
        db_session: Session,
    ) -> dict[str, Any]:
        """Process an experiment: run the agent pipeline over the dataset."""
        # Build agent configs from execution snapshot
        agent_configs = build_agent_configs_from_snapshot(execution, db_session)
        if not agent_configs:
            raise ValueError("No agent configurations found in execution snapshot")

        logger.info("Pipeline has %d agents", len(agent_configs))

        # Load dataset
        dataset_snapshot = json.loads(execution.dataset_snapshot)
        dataset_file_path = dataset_snapshot.get("file_path")
        sampling_config = dataset_snapshot.get("sampling_config", {})

        if not dataset_file_path:
            raise ValueError("Dataset file path not found in snapshot")

        chunks, total = await self._open_dataset(
            execution.workspace_id, dataset_file_path, sampling_config
        )
        self.progress.start(total)

        # Process all rows
        all_results: list[PipelineResult] = []
        total_processed = 0

        async for chunk_results, chunk_size in self._process_chunks(
            chunks, agent_configs
        ):
            all_results.extend(chunk_results)
            total_processed += chunk_size
            logger.info("Processed %d rows so far...", total_processed)

        return process_pipeline_results(execution, all_results, db_session)

    async def _open_dataset(
        self, workspace_id: int, dataset_file_path: str, sampling_config: dict
    ) -> tuple[AsyncGenerator[pd.DataFrame, None], int]:
        """Chunks of the rows to run, and how many rows there are in all."""
        dataset_full_path = validate_dataset_file(workspace_id, dataset_file_path)
        sampling_type = sampling_config.get("sampling_type", "all")

        if sampling_type == "random":
            df = apply_dataset_sampling(
                workspace_id, dataset_file_path, sampling_config
            )
            return self._dataframe_to_chunks(df), len(df)

        file_rows = await asyncio.to_thread(count_csv_rows, dataset_full_path)
        if sampling_type == "range":
            start_row = sampling_config.get("sampling_start_row", 1) - 1
            end_row = sampling_config.get("sampling_end_row")
            last_row = file_rows if end_row is None else min(end_row, file_rows)
            return (
                self._read_csv_range_chunks(dataset_full_path, start_row, end_row),
                max(last_row - start_row, 0),
            )
        return self._read_csv_chunks(dataset_full_path), file_rows

    async def _process_chunks(
        self,
        chunks: AsyncGenerator[pd.DataFrame, None],
        agent_configs: list[AgentConfig],
    ) -> AsyncGenerator[tuple, None]:
        """Yield (chunk_results, chunk_size) for each processed chunk."""
        chunk_number = 0
        async for chunk_df in chunks:
            chunk_number += 1
            logger.info("Processing chunk %d (%d rows)", chunk_number, len(chunk_df))
            chunk_results = await self._process_chunk(
                chunk_df,
                agent_configs,
                chunk_number,
            )
            yield chunk_results, len(chunk_df)

    async def _process_chunk(
        self,
        chunk_df: pd.DataFrame,
        agent_configs: list[AgentConfig],
        chunk_number: int,
    ) -> list[PipelineResult]:
        """Process a chunk of rows concurrently via the orchestrator."""
        # The DataFrame index is the row's position in the dataset file
        dataset_row_ids = [int(label) for label in chunk_df.index]
        tasks = []
        for idx, (_, row) in enumerate(chunk_df.iterrows()):
            row_index = idx + ((chunk_number - 1) * self.chunk_size) + 1
            tasks.append(
                self._run_pipeline_with_semaphore(
                    agent_configs, row.to_dict(), row_index, dataset_row_ids[idx]
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        pipeline_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                row_index = i + ((chunk_number - 1) * self.chunk_size) + 1
                logger.error("Row %d error: %s", row_index, result)
                pipeline_results.append(
                    PipelineResult(
                        row_index=row_index,
                        input_data={},
                        dataset_row_id=dataset_row_ids[i],
                        error=str(result),
                    )
                )
            else:
                pipeline_results.append(result)

        return pipeline_results

    async def _run_pipeline_with_semaphore(
        self,
        agent_configs: list[AgentConfig],
        row: dict,
        row_index: int,
        dataset_row_id: int,
    ) -> PipelineResult:
        """Run the orchestrator pipeline with concurrency limiting."""
        async with self.semaphore:
            try:
                result = await run_pipeline(
                    agent_configs, row, row_index, dataset_row_id
                )
            except Exception:
                self.progress.row_done(failed=True)
                raise
        self.progress.row_done(failed=bool(result.error))
        return result

    # ------------------------------------------------------------------
    # CSV reading helpers
    # ------------------------------------------------------------------

    async def _read_csv_chunks(
        self, file_path
    ) -> AsyncGenerator[pd.DataFrame, None]:
        for chunk in pd.read_csv(file_path, chunksize=self.chunk_size):
            yield chunk

    async def _read_csv_range_chunks(
        self, file_path, start_row: int, end_row: int | None
    ) -> AsyncGenerator[pd.DataFrame, None]:
        nrows = None if end_row is None else (end_row - start_row)
        skiprows = list(range(1, start_row + 1)) if start_row > 0 else None
        for chunk in pd.read_csv(
            file_path,
            chunksize=self.chunk_size,
            skiprows=skiprows,
            nrows=nrows,
        ):
            # Skipped rows restart the index at 0; shift it back to file positions
            chunk.index = chunk.index + start_row
            yield chunk

    async def _dataframe_to_chunks(
        self, df: pd.DataFrame
    ) -> AsyncGenerator[pd.DataFrame, None]:
        for i in range(0, len(df), self.chunk_size):
            yield df.iloc[i : i + self.chunk_size]
