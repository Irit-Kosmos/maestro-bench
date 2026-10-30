# MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
# Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
# Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Shared utilities for experiment processing: dataset sampling, execution
snapshots and results serialization.
"""

import json
import logging
import secrets
from datetime import UTC, datetime

import pandas as pd
from sqlmodel import Session, col, select

import credentials
import workspace_files
from core.formula import check_outputs, free_variables
from core.orchestrator import AGGREGATOR, AgentConfig, PipelineResult
from core.steps import agent_id_of, mapping_source, split_step, step_label
from dataset_utils import validate_dataset_file
from references import missing_ids
from schemas.experiments import ExperimentCreate
from tables import (
    Agent,
    AgentExecutionSnapshot,
    Batch,
    Dataset,
    Experiment,
    ExperimentAgentConfig,
    ExperimentExecution,
    Model,
    PromptVersion,
)

logger = logging.getLogger(__name__)


class ExperimentConfigError(ValueError):
    """The submitted agent configurations cannot make a runnable experiment."""


def apply_dataset_sampling(
    workspace_id: int, dataset_file_path: str, sampling_config: dict
) -> pd.DataFrame:
    """Apply sampling configuration to a dataset and return the sampled DataFrame."""
    dataset_full_path = validate_dataset_file(workspace_id, dataset_file_path)
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
    if sampling_type == "random":
        sampling_size = sampling_config.get("sampling_size")
        if sampling_size and sampling_size > 0:
            sample_size = min(sampling_size, len(df))
            return df.sample(
                n=sample_size, random_state=sampling_config.get("sampling_seed")
            )
        return df
    if sampling_type == "range":
        start_row = sampling_config.get("sampling_start_row")
        end_row = sampling_config.get("sampling_end_row")
        if start_row and end_row:
            start_idx = max(0, start_row - 1)
            end_idx = min(len(df), end_row)
            return df.iloc[start_idx:end_idx]
        return df
    return df


def new_sampling_seed(requested: int | None) -> int:
    """The seed asked for, or a fresh one."""
    return requested if requested is not None else secrets.randbelow(2**32)


def add_experiment(
    session: Session,
    exp_data: ExperimentCreate,
    *,
    name: str | None = None,
    agent_overrides: dict[str, dict] | None = None,
    batch_id: int | None = None,
    variant: str | None = None,
) -> Experiment:
    """Add an experiment and its agent configurations to the session.

    Flushes but does not commit, so that a caller creating several experiments
    can make them all-or-nothing. ``agent_overrides`` replaces fields of the
    submitted configuration of a step (how a batch varies its experiments).
    Steps are the keys of ``agent_configurations``: an agent may have several.

    Raises ExperimentConfigError when an aggregator cannot run, or when the
    request points to something that is not in the session's workspace.
    """
    _check_references(session, exp_data, agent_overrides)
    experiment = Experiment(
        name=name or exp_data.name,
        description=exp_data.description,
        dataset_id=exp_data.dataset_id,
        sampling_type=exp_data.sampling_type,
        sampling_size=exp_data.sampling_size,
        sampling_start_row=exp_data.sampling_start_row,
        sampling_end_row=exp_data.sampling_end_row,
        sampling_seed=new_sampling_seed(exp_data.sampling_seed)
        if exp_data.sampling_type == "random" and batch_id is None
        else None,
        batch_id=batch_id,
        variant=variant,
    )
    session.add(experiment)
    session.flush()
    experiment_id = int(experiment.id) if experiment.id is not None else 0

    # Create individual agent configurations for explicitly configured active steps
    default_execution_order = 1
    configs: list[tuple[Agent, ExperimentAgentConfig]] = []
    configurations = _by_step(exp_data.agent_configurations)
    overrides = _by_step(agent_overrides)
    if configurations:
        steps = sorted((split_step(step), step) for step in configurations)
        agents = {
            agent.id: agent
            for agent in session.exec(
                select(Agent).where(
                    col(Agent.id).in_({agent_id for (agent_id, _), _ in steps})
                )
            ).all()
        }
        labels: set[str] = set()
        for (agent_id, instance), step in steps:
            agent = agents[agent_id]
            agent_config = configurations.get(step)
            if not agent_config:
                continue
            if step in overrides:
                agent_config = {**agent_config, **overrides[step]}

            if not agent_config.get("is_active", True):
                logger.info("Skipping inactive agent %s (%s)", agent.id, agent.name)
                continue

            # Use frontend-provided execution_order if available, otherwise auto-increment
            execution_order = agent_config.get(
                "execution_order", default_execution_order
            )
            if "execution_order" not in agent_config:
                default_execution_order += 1

            # Persist per-agent input mappings if provided
            input_mappings = agent_config.get("input_mappings")
            input_mappings_json = (
                json.dumps(input_mappings) if input_mappings else None
            )

            label = _unique_label(agent.name, instance, labels)
            labels.add(label)
            identity = {
                "experiment_id": experiment_id,
                "agent_id": int(agent.id) if agent.id is not None else 0,
                "step_key": step,
                "label": None if label == agent.name else label,
            }

            if agent.kind == AGGREGATOR:
                formulas = agent_config.get("formulas") or []
                config = ExperimentAgentConfig(
                    **identity,
                    execution_order=execution_order,
                    is_active=True,
                    input_mappings=input_mappings_json,
                    formulas=json.dumps(formulas),
                )
                session.add(config)
                configs.append((agent, config))
                continue

            prompt_version_id = (
                agent_config.get("prompt_version_id")
                or agent.default_prompt_version_id
            )
            if not prompt_version_id:
                logger.warning(
                    "Agent %s (%s) has no prompt version, skipping",
                    agent.id,
                    agent.name,
                )
                continue

            model_id = agent_config.get("model_id") or agent.default_model_id
            if not model_id:
                logger.warning(
                    "Agent %s (%s) has no model, skipping", agent.id, agent.name
                )
                continue

            config = ExperimentAgentConfig(
                **identity,
                prompt_version_id=prompt_version_id,
                model_id=model_id,
                temperature=agent_config.get("temperature"),
                max_tokens=agent_config.get("max_tokens"),
                execution_order=execution_order,
                is_active=True,
                input_mappings=input_mappings_json,
            )
            session.add(config)
            configs.append((agent, config))

    _check_aggregators(configs)
    _check_mapped_agents(session, configs)
    session.flush()
    return experiment


def _by_step(configurations: dict | None) -> dict[str, dict]:
    """Per-step settings with their keys as text, however the caller wrote them."""
    return {str(step): config for step, config in (configurations or {}).items()}


def _unique_label(name: str, instance: int, taken: set[str]) -> str:
    """Name of a step: the agent's, then "name #2"… and never one already in use."""
    label = step_label(name, instance)
    while label in taken:
        instance += 1
        label = step_label(name, instance)
    return label


def _check_references(
    session: Session,
    exp_data: ExperimentCreate,
    agent_overrides: dict[str, dict] | None,
) -> None:
    """Everything an experiment is built from must be in the workspace it is created in."""
    steps = _by_step(exp_data.agent_configurations)
    try:
        agent_ids = [agent_id_of(step) for step in steps]
    except ValueError as e:
        raise ExperimentConfigError(str(e)) from e
    overrides = _by_step(agent_overrides)
    configurations = [
        {**(config or {}), **overrides.get(step, {})} for step, config in steps.items()
    ]
    for label, table, ids in (
        ("Dataset", Dataset, [exp_data.dataset_id]),
        ("Agent", Agent, agent_ids),
        (
            "Prompt version",
            PromptVersion,
            [c["prompt_version_id"] for c in configurations if c.get("prompt_version_id")],
        ),
        (
            "Model",
            Model,
            [c["model_id"] for c in configurations if c.get("model_id")],
        ),
    ):
        if missing := missing_ids(session, table, ids):
            raise ExperimentConfigError(f"{label} {missing[0]} not found")


def _check_mapped_agents(
    session: Session, configs: list[tuple[Agent, ExperimentAgentConfig]]
) -> None:
    """The agents whose outputs an agent reads must be in the workspace."""
    mapped = [
        mapping_source(mapping)
        for _, config in configs
        for mapping in json.loads(config.input_mappings or "[]")
        if isinstance(mapping, dict) and mapping.get("source") == "agent"
    ]
    try:
        agent_ids = [agent_id_of(step) for step in mapped if step is not None]
    except ValueError as e:
        raise ExperimentConfigError(str(e)) from e
    if missing := missing_ids(session, Agent, agent_ids):
        raise ExperimentConfigError(f"Agent {missing[0]} not found")


def _check_aggregators(configs: list[tuple[Agent, ExperimentAgentConfig]]) -> None:
    """Refuse aggregators whose formulas or variables cannot be evaluated."""
    names = {config.step_key: config.label or agent.name for agent, config in configs}
    orders = {config.step_key: config.execution_order for _, config in configs}
    for agent, config in configs:
        if agent.kind != AGGREGATOR:
            continue
        problems = aggregator_problems(
            json.loads(config.formulas or "[]"),
            json.loads(config.input_mappings or "[]"),
            {
                step: name
                for step, name in names.items()
                if orders[step] < config.execution_order
            },
            names,
        )
        if problems:
            raise ExperimentConfigError(
                f'Aggregator "{config.label or agent.name}": ' + "; ".join(problems)
            )


def aggregator_problems(
    formulas: list[dict],
    mappings: list[dict],
    upstream: dict[str, str],
    all_agents: dict[str, str],
) -> list[str]:
    """
    Why an aggregator cannot run, or an empty list.

    ``upstream`` names the steps that run before the aggregator, ``all_agents``
    every step of the experiment, both by step key.
    """
    if not formulas:
        return ["it has no formula"]
    problems = [
        f'output "{output.get("name") or "?"}": {error}'
        for output, error in zip(formulas, check_outputs(formulas), strict=True)
        if error
    ]
    by_variable = {m.get("variable"): m for m in mappings}
    for variable in free_variables(formulas):
        mapping = by_variable.get(variable) or {}
        source = mapping.get("source")
        if source == "agent":
            step = mapping_source(mapping)
            if step not in all_agents:
                problems.append(
                    f'variable "{variable}" reads an agent that is not in the experiment'
                )
            elif step not in upstream:
                problems.append(
                    f'variable "{variable}" reads {all_agents[step]}, '
                    "which does not run before the aggregator"
                )
        elif (source == "dataset" and mapping.get("sourceColumn")) or (source == "static" and str(mapping.get("staticValue") or "").strip()):
            continue
        elif source in ("dataset", "static"):
            problems.append(f'variable "{variable}" has no value')
        else:
            problems.append(f'variable "{variable}" is not mapped')
    return problems


def create_execution_snapshot(
    experiment_id: int, session: Session
) -> ExperimentExecution:
    """Create an immutable snapshot of the experiment configuration at execution time."""
    experiment = session.get(Experiment, experiment_id)
    if not experiment:
        raise ValueError(f"Experiment {experiment_id} not found")

    dataset = session.get(Dataset, experiment.dataset_id)

    # The seed is kept on the experiment and recorded in each execution, so that every
    # run takes the same rows, and can be compared row by row, until the sample is
    # redrawn. The experiments of a batch share the batch's seed instead, so that they
    # are all compared on the same rows.
    sampling_seed = None
    if experiment.sampling_type == "random":
        batch = session.get(Batch, experiment.batch_id) if experiment.batch_id else None
        if batch is not None and batch.sampling_seed is not None:
            sampling_seed = batch.sampling_seed
        else:
            if experiment.sampling_seed is None:
                experiment.sampling_seed = new_sampling_seed(None)
                session.add(experiment)
            sampling_seed = experiment.sampling_seed
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
                    "sampling_seed": sampling_seed,
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
        if execution.id is None or agent.id is None:
            continue

        if agent.kind == AGGREGATOR:
            session.add(
                AgentExecutionSnapshot(
                    execution_id=execution.id,
                    agent_id=agent.id,
                    step_key=agent_config.step_key,
                    kind=AGGREGATOR,
                    agent_name_snapshot=agent_config.label or agent.name,
                    model_name_snapshot="",
                    model_provider_snapshot="",
                    prompt_name_snapshot="",
                    prompt_version_snapshot="",
                    final_input_mappings=agent_config.input_mappings,
                    final_formulas=agent_config.formulas,
                    execution_order=agent_config.execution_order,
                )
            )
            continue

        prompt_version = session.get(
            PromptVersion,
            agent_config.prompt_version_id or agent.default_prompt_version_id,
        )
        model = session.get(Model, agent_config.model_id or agent.default_model_id)

        if not prompt_version or not model:
            continue

        agent_snapshot = AgentExecutionSnapshot(
            execution_id=execution.id,
            agent_id=agent.id,
            step_key=agent_config.step_key,
            agent_name_snapshot=agent_config.label or agent.name,
            model_name_snapshot=model.name,
            model_provider_snapshot=model.provider,
            prompt_name_snapshot=prompt_version.prompt.name
            if prompt_version.prompt
            else "Unknown",
            prompt_version_snapshot=prompt_version.version,
            prompt_id=prompt_version.prompt_id,
            prompt_version_id=prompt_version.id,
            final_system_prompt=prompt_version.system_prompt,
            final_user_prompt=prompt_version.user_prompt,
            final_variables=prompt_version.variables,
            # An explicit 0 is a real choice, not "use the model's default"
            final_temperature=agent_config.temperature
            if agent_config.temperature is not None
            else (model.default_temperature or 0.0),
            final_max_tokens=agent_config.max_tokens or model.default_max_tokens,
            final_input_mappings=agent_config.input_mappings,
            execution_order=agent_config.execution_order,
        )
        session.add(agent_snapshot)

    session.commit()
    logger.info(
        "Created execution snapshot %s for experiment %s with %d agent configs",
        execution.id,
        experiment_id,
        len(agent_configs),
    )
    return execution


def build_agent_configs_from_snapshot(
    execution: ExperimentExecution, session: Session
) -> list[AgentConfig]:
    """Build core.orchestrator.AgentConfig list from execution snapshots."""
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

        # Parse input mappings
        input_mappings = []
        if snapshot.final_input_mappings:
            try:
                input_mappings = json.loads(snapshot.final_input_mappings)
                if not isinstance(input_mappings, list):
                    input_mappings = []
            except (json.JSONDecodeError, TypeError):
                pass

        agents.append(
            AgentConfig(
                name=snapshot.agent_name_snapshot,
                system_prompt=snapshot.final_system_prompt,
                user_prompt=snapshot.final_user_prompt,
                variables=variables,
                model=snapshot.model_name_snapshot,
                provider=snapshot.model_provider_snapshot,
                temperature=snapshot.final_temperature or 0.0,
                max_tokens=snapshot.final_max_tokens,
                execution_order=snapshot.execution_order,
                input_mappings=input_mappings,
                agent_id=snapshot.agent_id,
                step_key=snapshot.step_key,
                kind=snapshot.kind,
                formulas=json.loads(snapshot.final_formulas)
                if snapshot.final_formulas
                else None,
            )
        )

    # Each provider is reached with the workspace's own key when it has one
    accesses: dict[str, credentials.ProviderAccess] = {}
    for agent in agents:
        if agent.provider not in accesses:
            accesses[agent.provider] = credentials.access_to(session, agent.provider)
        agent.api_key = accesses[agent.provider].api_key
        agent.key_id = accesses[agent.provider].key_id
        agent.access_error = accesses[agent.provider].error

    return agents


def process_pipeline_results(
    execution: ExperimentExecution,
    pipeline_results: list[PipelineResult],
    session: Session | None = None,
) -> dict:
    """
    Process pipeline results and save them to disk.

    Args:
        execution: The experiment execution
        pipeline_results: List of PipelineResult from the orchestrator
        session: Database session

    Returns:
        Summary dict with aggregated metrics
    """
    results_dir = workspace_files.results_dir(execution.workspace_id)
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")[:-3]
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
        rows.append(row_data)
        total_tokens_in += result.total_tokens_in
        total_tokens_out += result.total_tokens_out
        total_cost += result.total_cost_usd
        total_latency += result.total_latency_ms

    processing_time = (datetime.now(UTC) - execution.started_at).total_seconds()

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
        },
        "rows": rows,
        "configuration_used": _build_config_snapshot(execution, session),
        "maestro_bench_version": "2.0.0",
        "completed_at": datetime.now(UTC).isoformat(),
    }

    with open(results_file_path, "w") as f:
        json.dump(complete_results, f, indent=2, default=str)

    logger.info("Results saved to %s", results_file_path)

    # Stored relative to the workspace's results folder so the data can be moved around
    stored_path = str(results_file_path.relative_to(results_dir))
    if session:
        execution.results_file_path = stored_path
        # Store summary metrics on execution record
        execution.total_tokens = total_tokens_in + total_tokens_out
        execution.total_cost_usd = round(total_cost, 6)
        session.add(execution)
        _store_step_usage(execution, pipeline_results, session)
        session.commit()

    return {
        "processing_time_seconds": processing_time,
        "results_file_path": stored_path,
        "total_rows": len(pipeline_results),
        "total_cost_usd": round(total_cost, 6),
    }


def _store_step_usage(
    execution: ExperimentExecution,
    pipeline_results: list[PipelineResult],
    session: Session,
) -> None:
    """Put on each step's snapshot the tokens and cost it used over all the rows."""
    used: dict[str, tuple[int, float]] = {}
    for result in pipeline_results:
        for trace in result.agent_traces:
            if trace.step_key is None:
                continue
            tokens, cost = used.get(trace.step_key, (0, 0.0))
            used[trace.step_key] = (
                tokens + trace.tokens_in + trace.tokens_out,
                cost + trace.cost_usd,
            )
    for snapshot in execution.agent_snapshots:
        # A trace knows its step the way the orchestrator does: its key, or its agent
        key = snapshot.step_key or (
            str(snapshot.agent_id) if snapshot.agent_id is not None else None
        )
        tokens, cost = used.get(key, (0, 0.0)) if key else (0, 0.0)
        snapshot.total_tokens = tokens
        snapshot.total_cost_usd = round(cost, 6)
        session.add(snapshot)


def _build_config_snapshot(
    execution: ExperimentExecution, session: Session | None
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
                "step_key": s.step_key or (None if s.agent_id is None else str(s.agent_id)),
                "agent_name": s.agent_name_snapshot,
                "kind": s.kind,
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
                "input_mappings": json.loads(s.final_input_mappings)
                if s.final_input_mappings
                else [],
                **(
                    {"formulas": json.loads(s.final_formulas)}
                    if s.final_formulas
                    else {}
                ),
            }
            for s in agent_snapshots
        ],
    }
