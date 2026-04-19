"""
Shared utilities for experiment processing.
Contains functions used by both sync and async experiment processors.

V2: Uses core engine (LiteLLM + orchestrator) instead of external MAESTRO API.
"""

import json
import pandas as pd
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
from sqlmodel import Session, select

from tables import (
    Experiment,
    ExperimentAgentConfig,
    Agent,
    Dataset,
    ExperimentExecution,
    AgentExecutionSnapshot,
    PromptVersion,
    Model,
)
from dataset_utils import validate_dataset_file
from core.orchestrator import AgentConfig, PipelineResult


def apply_column_mappings(
    dataset_row: dict, column_mappings_json: Optional[str]
) -> dict:
    """
    Apply column mappings to transform dataset columns into expected prompt variables.

    Supports both V1 format (JSON list of {sourceColumn, targetField}) and
    V2 format (simple dict of source → target, stored as JSON string).
    """
    if not column_mappings_json:
        return dataset_row.copy()

    try:
        column_mappings = json.loads(column_mappings_json)

        # V2 format: simple dict
        if isinstance(column_mappings, dict):
            mapped_data = {}
            for source, target in column_mappings.items():
                if source in dataset_row:
                    mapped_data[target] = dataset_row[source]
            return mapped_data

        # V1 format: list of {sourceColumn, targetField}
        if isinstance(column_mappings, list):
            mapped_data = {}
            for mapping in column_mappings:
                if (
                    isinstance(mapping, dict)
                    and "sourceColumn" in mapping
                    and "targetField" in mapping
                ):
                    source_column = mapping["sourceColumn"]
                    target_field = mapping["targetField"]
                    if source_column in dataset_row:
                        mapped_data[target_field] = dataset_row[source_column]
            return mapped_data

        return dataset_row.copy()

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"[ExperimentUtils] Error applying column mappings: {e}")
        return dataset_row.copy()


def apply_dataset_sampling(
    dataset_file_path: str, sampling_config: dict
) -> pd.DataFrame:
    """Apply sampling configuration to a dataset and return the sampled DataFrame."""
    dataset_full_path = validate_dataset_file(dataset_file_path)
    file_extension = dataset_full_path.suffix.lower()

    if file_extension == ".csv":
        df = pd.read_csv(dataset_full_path)
    elif file_extension == ".json":
        df = pd.read_json(dataset_full_path)
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")

    sampling_type = sampling_config.get("sampling_type", "all")

    if sampling_type == "all" or sampling_type is None:
        return df
    elif sampling_type == "random":
        sampling_size = sampling_config.get("sampling_size")
        if sampling_size and sampling_size > 0:
            sample_size = min(sampling_size, len(df))
            return df.sample(n=sample_size)
        return df
    elif sampling_type == "range":
        start_row = sampling_config.get("sampling_start_row")
        end_row = sampling_config.get("sampling_end_row")
        if start_row and end_row:
            start_idx = max(0, start_row - 1)
            end_idx = min(len(df), end_row)
            return df.iloc[start_idx:end_idx]
        return df
    else:
        return df


def create_execution_snapshot(
    experiment_id: int, session: Session
) -> ExperimentExecution:
    """Create an immutable snapshot of the experiment configuration at execution time."""
    experiment = session.get(Experiment, experiment_id)
    if not experiment:
        raise Exception(f"Experiment {experiment_id} not found")

    dataset = session.get(Dataset, experiment.dataset_id)
    dataset_snapshot = (
        json.dumps(
            {
                "id": dataset.id,
                "name": dataset.name,
                "description": dataset.description,
                "file_path": dataset.file_path,
                "sampling_config": {
                    "sampling_type": experiment.sampling_type,
                    "sampling_size": experiment.sampling_size,
                    "sampling_start_row": experiment.sampling_start_row,
                    "sampling_end_row": experiment.sampling_end_row,
                },
            }
        )
        if dataset
        else "{}"
    )

    execution = ExperimentExecution(
        experiment_id=experiment_id, dataset_snapshot=dataset_snapshot
    )
    session.add(execution)
    session.commit()
    session.refresh(execution)

    # Get agent configurations for this experiment
    agent_configs = session.exec(
        select(ExperimentAgentConfig).where(
            ExperimentAgentConfig.experiment_id == experiment_id,
            ExperimentAgentConfig.is_active,
        )
    ).all()

    for agent_config in agent_configs:
        agent = session.get(Agent, agent_config.agent_id)
        if not agent:
            continue

        prompt_version = session.get(
            PromptVersion,
            agent_config.prompt_version_id or agent.default_prompt_version_id,
        )
        model = session.get(Model, agent_config.model_id or agent.default_model_id)

        if not prompt_version or not model:
            continue
        if execution.id is None or agent.id is None:
            continue

        agent_snapshot = AgentExecutionSnapshot(
            execution_id=execution.id,
            agent_id=agent.id,
            agent_name_snapshot=agent.name,
            model_name_snapshot=model.name,
            model_provider_snapshot=model.provider,
            prompt_name_snapshot=prompt_version.prompt.name
            if prompt_version.prompt
            else "Unknown",
            prompt_version_snapshot=prompt_version.version,
            final_system_prompt=prompt_version.system_prompt,
            final_user_prompt=prompt_version.user_prompt,
            final_variables=prompt_version.variables,
            final_temperature=agent_config.temperature
            or model.default_temperature
            or 0.0,
            final_max_tokens=agent_config.max_tokens or model.default_max_tokens,
            execution_order=agent_config.execution_order,
        )
        session.add(agent_snapshot)

    session.commit()
    print(
        f"[ExperimentUtils] Created execution snapshot {execution.id} for experiment {experiment_id} with {len(agent_configs)} agent configs"
    )
    return execution


def build_agent_configs_from_snapshot(
    execution: ExperimentExecution, session: Session
) -> list[AgentConfig]:
    """
    Build core.orchestrator.AgentConfig list from execution snapshots.
    Replaces the old build_maestro_request_payload().
    """
    agent_snapshots = session.exec(
        select(AgentExecutionSnapshot)
        .where(AgentExecutionSnapshot.execution_id == execution.id)
        .order_by(AgentExecutionSnapshot.execution_order)
    ).all()

    agents = []
    for snapshot in agent_snapshots:
        # Parse variables
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

        team_name = "Unknown"
        if snapshot.agent and snapshot.agent.team:
            team_name = snapshot.agent.team.name

        agents.append(
            AgentConfig(
                name=snapshot.agent_name_snapshot,
                team_name=team_name,
                system_prompt=snapshot.final_system_prompt,
                user_prompt=snapshot.final_user_prompt,
                variables=variables,
                model=snapshot.model_name_snapshot,
                provider=snapshot.model_provider_snapshot,
                temperature=snapshot.final_temperature or 0.0,
                max_tokens=snapshot.final_max_tokens,
                execution_order=snapshot.execution_order,
            )
        )

    return agents


def process_pipeline_results(
    execution: ExperimentExecution,
    pipeline_results: list[PipelineResult],
    scores: Optional[dict] = None,
    session: Optional[Session] = None,
) -> dict:
    """
    Process pipeline results and save them to disk.
    Replaces the old process_maestro_results().

    Args:
        execution: The experiment execution
        pipeline_results: List of PipelineResult from the orchestrator
        scores: Optional dict of {row_index: {scorer_name: ScoreResult}}
        session: Database session

    Returns:
        Summary dict with aggregated metrics
    """
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    results_file_path = (
        results_dir
        / f"experiment_{execution.experiment_id}_execution_{execution.id}_{timestamp}_results.json"
    )

    # Serialize results
    rows = []
    total_tokens_in = 0
    total_tokens_out = 0
    total_cost = 0.0
    total_latency = 0.0

    for result in pipeline_results:
        row_data = result.to_dict()

        # Attach scores if available
        if scores and result.row_index in scores:
            row_data["scores"] = {
                name: {
                    "score": sr.score,
                    "raw_value": sr.raw_value,
                    "details": sr.details,
                }
                for name, sr in scores[result.row_index].items()
            }

        rows.append(row_data)
        total_tokens_in += result.total_tokens_in
        total_tokens_out += result.total_tokens_out
        total_cost += result.total_cost_usd
        total_latency += result.total_latency_ms

    # Compute score averages
    score_averages = {}
    if scores:
        all_scorer_names = set()
        for row_scores in scores.values():
            all_scorer_names.update(row_scores.keys())
        for scorer_name in all_scorer_names:
            vals = [
                row_scores[scorer_name].score
                for row_scores in scores.values()
                if scorer_name in row_scores
            ]
            if vals:
                score_averages[scorer_name] = round(sum(vals) / len(vals), 4)

    started_at = execution.started_at if execution.started_at.tzinfo is not None else execution.started_at.replace(tzinfo=timezone.utc)
    processing_time = (datetime.now(timezone.utc) - started_at).total_seconds()

    complete_results = {
        "execution_id": execution.id,
        "experiment_id": execution.experiment_id,
        "processing_time_seconds": processing_time,
        "summary": {
            "total_rows": len(pipeline_results),
            "total_tokens_in": total_tokens_in,
            "total_tokens_out": total_tokens_out,
            "total_cost_usd": round(total_cost, 6),
            "total_latency_ms": round(total_latency, 1),
            "avg_latency_ms": round(total_latency / len(pipeline_results), 1)
            if pipeline_results
            else 0,
            "avg_scores": score_averages,
        },
        "rows": rows,
        "configuration_used": _build_config_snapshot(execution, session),
        "maestro_bench_version": "2.0.0",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(results_file_path, "w") as f:
        json.dump(complete_results, f, indent=2, default=str)

    print(f"[ExperimentUtils] Results saved to {results_file_path}")

    if session:
        execution.results_file_path = str(results_file_path)
        # Store summary metrics on execution record
        execution.total_tokens = total_tokens_in + total_tokens_out
        execution.total_cost_usd = round(total_cost, 6)
        execution.scores_summary = json.dumps(score_averages) if score_averages else None
        session.add(execution)
        session.commit()

    return {
        "processing_time_seconds": processing_time,
        "results_file_path": str(results_file_path),
        "total_rows": len(pipeline_results),
        "total_cost_usd": round(total_cost, 6),
        "avg_scores": score_averages,
    }


def _build_config_snapshot(
    execution: ExperimentExecution, session: Optional[Session]
) -> dict:
    """Build the configuration snapshot for the results file."""
    if not session:
        return {"execution_id": execution.id}

    agent_snapshots = session.exec(
        select(AgentExecutionSnapshot)
        .where(AgentExecutionSnapshot.execution_id == execution.id)
        .order_by(AgentExecutionSnapshot.execution_order)
    ).all()

    return {
        "execution_id": execution.id,
        "dataset_snapshot": json.loads(execution.dataset_snapshot),
        "agents": [
            {
                "agent_id": s.agent_id,
                "agent_name": s.agent_name_snapshot,
                "model_name": s.model_name_snapshot,
                "model_provider": s.model_provider_snapshot,
                "prompt_name": s.prompt_name_snapshot,
                "prompt_version": s.prompt_version_snapshot,
                "system_prompt": s.final_system_prompt,
                "user_prompt": s.final_user_prompt,
                "variables": json.loads(s.final_variables) if s.final_variables else [],
                "temperature": s.final_temperature,
                "max_tokens": s.final_max_tokens,
                "execution_order": s.execution_order,
            }
            for s in agent_snapshots
        ],
    }
