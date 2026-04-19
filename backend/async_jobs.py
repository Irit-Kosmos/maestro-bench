"""
Async experiment processor.

V2: Uses core engine (LiteLLM + orchestrator + scorer) instead of external MAESTRO API.
Experiments are dispatched as native asyncio Tasks on uvicorn's event loop.
"""

import asyncio
import json
import pandas as pd
from datetime import datetime, timezone
from typing import Optional, AsyncGenerator, Dict, Any
from sqlmodel import Session, select

from db import engine
from tables import Experiment, ExperimentExecution
from dataset_utils import validate_dataset_file
from core.orchestrator import AgentConfig, PipelineResult, run_pipeline
from core.scorer import BaseScorer, ScoreResult, create_scorer

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CHUNK_SIZE = 5
DEFAULT_MAX_CONCURRENT = 2

# ---------------------------------------------------------------------------
# Task registry — maps experiment_id → running asyncio.Task
# ---------------------------------------------------------------------------

_running_tasks: Dict[int, asyncio.Task] = {}


def start_experiment(experiment_id: int) -> bool:
    """Schedule an experiment run as a background asyncio Task."""
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
    """Cancel a running experiment task."""
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
        with Session(engine) as db_session:
            experiment = db_session.get(Experiment, experiment_id)
            if not experiment:
                print(f"[AsyncJob] Experiment {experiment_id} not found")
                return

            print(f"[AsyncJob] Found experiment: {experiment.name}")
            experiment.status = "running"
            db_session.add(experiment)
            db_session.commit()

            # Create immutable execution snapshot
            from experiment_utils import create_execution_snapshot

            execution = create_execution_snapshot(experiment_id, db_session)
            print(f"[AsyncJob] Created execution snapshot {execution.id}")

            # Run the experiment pipeline
            processor = _ExperimentProcessor(
                chunk_size=DEFAULT_CHUNK_SIZE,
                max_concurrent=DEFAULT_MAX_CONCURRENT,
            )
            results_summary = await processor.process_experiment(
                execution, db_session
            )

            execution.status = "completed"
            execution.completed_at = datetime.now(timezone.utc)
            experiment.status = "completed"
            experiment.completed_at = datetime.now(timezone.utc)

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
        import traceback

        traceback.print_exc()
        await _mark_experiment_failed(experiment_id, str(e))


async def _mark_experiment_failed(experiment_id: int, error_msg: str) -> None:
    """Mark experiment and any running executions as failed."""
    try:
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
                    exc.completed_at = datetime.now(timezone.utc)
                    db_session.add(exc)

                db_session.commit()
                print(
                    f"[AsyncJob] Marked experiment {experiment_id} as failed: {error_msg}"
                )
    except Exception as e:
        print(f"[AsyncJob] Failed to mark experiment as failed: {e}")


# ---------------------------------------------------------------------------
# Experiment processor — uses core engine
# ---------------------------------------------------------------------------


class _ExperimentProcessor:
    """Processes experiments using the core pipeline engine."""

    def __init__(self, chunk_size: int = 5, max_concurrent: int = 2):
        self.chunk_size = chunk_size
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def process_experiment(
        self,
        execution: ExperimentExecution,
        db_session: Session,
    ) -> Dict[str, Any]:
        """Process an experiment: run pipeline + optional scoring."""
        from experiment_utils import (
            build_agent_configs_from_snapshot,
            process_pipeline_results,
        )

        # Build agent configs from execution snapshot
        agent_configs = build_agent_configs_from_snapshot(execution, db_session)
        if not agent_configs:
            raise ValueError("No agent configurations found in execution snapshot")

        print(f"[AsyncJob] Pipeline has {len(agent_configs)} agents")

        # Load dataset
        dataset_snapshot = json.loads(execution.dataset_snapshot)
        dataset_file_path = dataset_snapshot.get("file_path")
        sampling_config = dataset_snapshot.get("sampling_config", {})

        if not dataset_file_path:
            raise ValueError("Dataset file path not found in snapshot")

        # Get column mappings from experiment
        experiment = db_session.get(Experiment, execution.experiment_id)
        column_mappings_json = experiment.column_mappings if experiment else None

        # Process all rows
        all_results: list[PipelineResult] = []
        total_processed = 0

        async for chunk_results, chunk_size in self._process_chunks(
            dataset_file_path,
            sampling_config,
            agent_configs,
            column_mappings_json,
        ):
            all_results.extend(chunk_results)
            total_processed += chunk_size
            print(f"[AsyncJob] Processed {total_processed} rows so far...")

        # Optional scoring
        scores = await self._run_scoring(execution, all_results, db_session)

        return process_pipeline_results(execution, all_results, scores, db_session)

    async def _process_chunks(
        self,
        dataset_file_path: str,
        sampling_config: dict,
        agent_configs: list[AgentConfig],
        column_mappings_json: Optional[str],
    ) -> AsyncGenerator[tuple, None]:
        """Yield (chunk_results, chunk_size) for each processed chunk."""
        from experiment_utils import apply_dataset_sampling

        dataset_full_path = validate_dataset_file(dataset_file_path)
        sampling_type = sampling_config.get("sampling_type", "all")

        if sampling_type == "all":
            chunk_iter = self._read_csv_chunks(dataset_full_path)
        elif sampling_type == "random":
            df = apply_dataset_sampling(dataset_file_path, sampling_config)
            chunk_iter = self._dataframe_to_chunks(df)
        elif sampling_type == "range":
            start_row = sampling_config.get("sampling_start_row", 1) - 1
            end_row = sampling_config.get("sampling_end_row")
            chunk_iter = self._read_csv_range_chunks(
                dataset_full_path, start_row, end_row
            )
        else:
            chunk_iter = self._read_csv_chunks(dataset_full_path)

        chunk_number = 0
        async for chunk_df in chunk_iter:
            chunk_number += 1
            print(
                f"[AsyncJob] Processing chunk {chunk_number} ({len(chunk_df)} rows)"
            )
            chunk_results = await self._process_chunk(
                chunk_df,
                agent_configs,
                column_mappings_json,
                chunk_number,
            )
            yield chunk_results, len(chunk_df)

    async def _process_chunk(
        self,
        chunk_df: pd.DataFrame,
        agent_configs: list[AgentConfig],
        column_mappings_json: Optional[str],
        chunk_number: int,
    ) -> list[PipelineResult]:
        """Process a chunk of rows concurrently via the orchestrator."""
        from experiment_utils import apply_column_mappings

        tasks = []
        for idx, (_, row) in enumerate(chunk_df.iterrows()):
            row_index = idx + ((chunk_number - 1) * self.chunk_size) + 1
            row_dict = row.to_dict()
            mapped_data = apply_column_mappings(row_dict, column_mappings_json)

            tasks.append(
                self._run_pipeline_with_semaphore(
                    agent_configs, mapped_data, row_index
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        pipeline_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                row_index = i + ((chunk_number - 1) * self.chunk_size) + 1
                print(f"[AsyncJob] Row {row_index} error: {result}")
                pipeline_results.append(
                    PipelineResult(
                        row_index=row_index,
                        input_data={},
                        error=str(result),
                    )
                )
            else:
                pipeline_results.append(result)

        return pipeline_results

    async def _run_pipeline_with_semaphore(
        self,
        agent_configs: list[AgentConfig],
        data: dict,
        row_index: int,
    ) -> PipelineResult:
        """Run the orchestrator pipeline with concurrency limiting."""
        async with self.semaphore:
            return await run_pipeline(agent_configs, data, row_index)

    async def _run_scoring(
        self,
        execution: ExperimentExecution,
        results: list[PipelineResult],
        db_session: Session,
    ) -> Optional[dict]:
        """Run scoring on pipeline results if scoring config exists."""
        experiment = db_session.get(Experiment, execution.experiment_id)
        if not experiment or not experiment.scoring_config:
            return None

        try:
            scoring_configs = json.loads(experiment.scoring_config)
            if not scoring_configs:
                return None
        except (json.JSONDecodeError, TypeError):
            return None

        scorers: list[tuple[BaseScorer, dict]] = []
        for sc in scoring_configs:
            scorer = create_scorer(sc)
            scorers.append((scorer, sc))

        # Get original dataset rows for reference columns
        dataset_snapshot = json.loads(execution.dataset_snapshot)
        dataset_file_path = dataset_snapshot.get("file_path")
        if not dataset_file_path:
            return None

        # For now, scoring uses final_output vs reference_column
        # TODO: support prediction_field extraction from structured output
        all_scores: dict[int, dict[str, ScoreResult]] = {}

        for result in results:
            if result.error:
                continue

            row_scores = {}
            for scorer, sc_config in scorers:
                reference_col = sc_config.get("reference_column")
                reference_val = ""
                if reference_col and reference_col in result.input_data:
                    reference_val = str(result.input_data[reference_col])

                score_result = await scorer.score(
                    prediction=result.final_output,
                    reference=reference_val,
                )
                row_scores[scorer.name] = score_result

            all_scores[result.row_index] = row_scores

        return all_scores

    # ------------------------------------------------------------------
    # CSV reading helpers (unchanged from V1)
    # ------------------------------------------------------------------

    async def _read_csv_chunks(
        self, file_path
    ) -> AsyncGenerator[pd.DataFrame, None]:
        for chunk in pd.read_csv(file_path, chunksize=self.chunk_size):
            yield chunk

    async def _read_csv_range_chunks(
        self, file_path, start_row: int, end_row: Optional[int]
    ) -> AsyncGenerator[pd.DataFrame, None]:
        nrows = None if end_row is None else (end_row - start_row)
        skiprows = list(range(1, start_row + 1)) if start_row > 0 else None
        for chunk in pd.read_csv(
            file_path,
            chunksize=self.chunk_size,
            skiprows=skiprows,
            nrows=nrows,
        ):
            yield chunk

    async def _dataframe_to_chunks(
        self, df: pd.DataFrame
    ) -> AsyncGenerator[pd.DataFrame, None]:
        for i in range(0, len(df), self.chunk_size):
            yield df.iloc[i : i + self.chunk_size]
