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

import json
import logging
from collections import Counter, defaultdict
from collections.abc import Iterable

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, col, select

import async_jobs
from batch_utils import (
    DATASET_AXIS,
    DATASET_FIELD,
    MAX_BATCH_EXPERIMENTS,
    VariationError,
    batch_status,
    column_map_of,
    expand_variations,
    format_temperature,
    is_base_point,
    is_dataset_axis,
    normalize_variations,
    parse_point,
    prompt_variable_names,
    serialize_point,
    unmapped_variables,
    variant_label,
    variation_step,
)
from core.orchestrator import AGGREGATOR
from core.steps import agent_id_of, split_step, step_label
from dataset_utils import dataset_shape, validate_dataset_file
from db import SessionDep
from execution_stats import latest_figures
from experiment_utils import (
    ExperimentConfigError,
    add_experiment,
    check_column_map,
    new_sampling_seed,
)
from loading import by_id, grouped_by, people
from results_files import execution_row_count
from schemas.batches import (
    BatchCancelResponse,
    BatchCreate,
    BatchExperimentResponse,
    BatchRerunResponse,
    BatchResponse,
    VariantCoordinate,
    VariationResponse,
    VariationValueResponse,
)
from schemas.experiments import ExperimentCreate
from schemas.people import PersonResponse
from study_utils import clear_item_links
from tables import (
    Agent,
    AgentExecutionSnapshot,
    Batch,
    Dataset,
    Experiment,
    ExperimentExecution,
    Model,
    Prompt,
    PromptVersion,
)
from workspace_scope import current_user_id, current_workspace_id

router = APIRouter(tags=["batches"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


class _Labels:
    """Names the rows a batch's values point to, each one looked up once.

    `preload` fetches many rows in one query. A row that is not found is
    remembered as missing, so a dangling id costs a single query too.
    """

    def __init__(self, session: Session):
        self._session = session
        self._rows: dict[tuple[type, int], object | None] = {}

    def preload(self, table: type, ids: Iterable[int | None]) -> None:
        wanted = {i for i in ids if i is not None and (table, i) not in self._rows}
        found = by_id(self._session, table, wanted)
        for row_id in wanted:
            self._rows[(table, row_id)] = found.get(row_id)

    def get(self, table: type, row_id: int):
        if (table, row_id) not in self._rows:
            self._rows[(table, row_id)] = self._session.get(table, row_id)
        return self._rows[(table, row_id)]


def _value_label(field: str, value: int | float | None, labels: _Labels) -> str:
    """Human-readable name of a value of a varied field."""
    if field == "temperature":
        return format_temperature(None if value is None else float(value))
    if field == DATASET_FIELD:
        dataset = labels.get(Dataset, int(value))
        return dataset.name if dataset else f"dataset {value}"
    if field == "model_id":
        model = labels.get(Model, int(value))
        return model.name if model else f"model {value}"
    version = labels.get(PromptVersion, int(value))
    if version is None:
        return f"prompt {value}"
    prompt = labels.get(Prompt, version.prompt_id)
    prompt_name = prompt.name if prompt else "Prompt"
    return f"{prompt_name} v{version.version}"


def _agent_name(step: str, labels: _Labels) -> str:
    """Name of a step of a batch: its agent's, then "name #2"…"""
    if step == DATASET_AXIS:
        return "Dataset"
    agent_id, instance = split_step(step)
    agent = labels.get(Agent, agent_id)
    return step_label(agent.name, instance) if agent else f"agent {agent_id}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _base_values(
    data: BatchCreate, variations: list[dict], session: Session
) -> dict[tuple[str, str], int | float | None]:
    """The value each varied field has in the base configuration."""
    values: dict[tuple[str, str], int | float | None] = {}
    for variation in variations:
        step, field = variation_step(variation), variation["field"]
        if is_dataset_axis(variation):
            values[(step, field)] = data.config.dataset_id
            continue
        config = data.config.agent_configurations.get(step) or {}
        value = config.get(field)
        if value is None and field != "temperature":
            agent = session.get(Agent, agent_id_of(step))
            default = None
            if agent:
                default = (
                    agent.default_model_id
                    if field == "model_id"
                    else agent.default_prompt_version_id
                )
            value = default
        values[(step, field)] = value
    return values


def _validate_batch(
    data: BatchCreate, variations: list[dict], total: int, session: Session
):
    """Raise HTTP 422 unless every experiment of the batch can run.

    Everything is checked before anything is written, so a bad request never
    leaves half a batch behind.
    """

    def fail(detail: str):
        raise HTTPException(status_code=422, detail=detail)

    if not session.get(Dataset, data.config.dataset_id):
        fail(f"Dataset {data.config.dataset_id} not found")
    if data.base_experiment_id and not session.get(
        Experiment, data.base_experiment_id
    ):
        fail(f"Base experiment {data.base_experiment_id} not found")
    if data.config.column_map:
        # The other datasets' columns stand for the base dataset's as it is on disk
        if any(is_dataset_axis(v) for v in variations):
            fail(
                "A dataset read under other column names cannot be varied: "
                "start from the base experiment of its batch"
            )
        try:
            check_column_map(session, data.config.dataset_id, data.config.column_map)
        except ExperimentConfigError as e:
            fail(str(e))

    if total < 1:
        fail("Nothing to run: the only experiment would repeat the base experiment")
    if total > MAX_BATCH_EXPERIMENTS:
        fail(
            f"This batch would create {total} experiments "
            f"(the maximum is {MAX_BATCH_EXPERIMENTS})"
        )

    configs = {str(step): config for step, config in data.config.agent_configurations.items()}
    varied: dict[str, dict[str, list]] = {}
    for variation in variations:
        if is_dataset_axis(variation):
            continue
        varied.setdefault(variation_step(variation), {})[variation["field"]] = variation[
            "values"
        ]

    # The base configuration: every active agent must end up with a prompt and a
    # model, otherwise the experiment would silently skip it
    active_agents = 0
    for step, config in configs.items():
        if not config or not config.get("is_active", True):
            continue
        try:
            agent = session.get(Agent, agent_id_of(step))
        except ValueError:
            fail(f"Invalid step '{step}'")
        if not agent:
            continue
        active_agents += 1
        if agent.kind == AGGREGATOR:
            # Computed from formulas: no prompt and no model
            continue
        axes = varied.get(step, {})
        if not (
            "prompt_version_id" in axes
            or config.get("prompt_version_id")
            or agent.default_prompt_version_id
        ):
            fail(f"Agent '{_agent_name(step, _Labels(session))}' has no prompt version")
        if not (
            "model_id" in axes or config.get("model_id") or agent.default_model_id
        ):
            fail(f"Agent '{_agent_name(step, _Labels(session))}' has no model")
    if active_agents == 0:
        fail("The batch has no active agent")

    for step, axes in varied.items():
        agent = session.get(Agent, agent_id_of(step))
        config = configs.get(step)
        if not agent or not config or not config.get("is_active", True):
            fail(f"Step {step} is not an active step of the batch")
        assert agent is not None

        for model_id in axes.get("model_id", []):
            if not session.get(Model, int(model_id)):
                fail(f"Model {model_id} not found")

        for version_id in axes.get("prompt_version_id", []):
            version = session.get(PromptVersion, int(version_id))
            if not version:
                fail(f"Prompt version {version_id} not found")
            assert version is not None
            missing = unmapped_variables(
                prompt_variable_names(version.variables), config.get("input_mappings")
            )
            if missing:
                fail(
                    f"Agent '{_agent_name(step, _Labels(session))}': prompt "
                    f"'{_value_label('prompt_version_id', version_id, _Labels(session))}' "
                    f"needs variables with no input mapping: "
                    f"{', '.join(sorted(missing))}"
                )

    dataset_axis = next((v for v in variations if is_dataset_axis(v)), None)
    if dataset_axis:
        _validate_datasets(data, dataset_axis, configs, varied, session)


def _validate_datasets(
    data: BatchCreate,
    axis: dict,
    configs: dict[str, dict],
    varied: dict[str, dict[str, list]],
    session: Session,
):
    """Raise HTTP 422 unless every dataset of the axis can stand for the base one.

    Each dataset must have a column for every column of the base dataset the
    configuration reads, under its own name or one the axis maps it to.
    """

    def fail(detail: str):
        raise HTTPException(status_code=422, detail=detail)

    workspace_id = current_workspace_id(session)

    def shape(dataset: Dataset) -> tuple[list[str], int]:
        try:
            if not dataset.file_path:
                raise FileNotFoundError("no file")
            return dataset_shape(validate_dataset_file(workspace_id, dataset.file_path))
        except (OSError, ValueError) as e:
            fail(f"Dataset '{dataset.name}' cannot be read: {e}")
            raise

    base = session.get(Dataset, data.config.dataset_id)
    if not base:
        fail(f"Dataset {data.config.dataset_id} not found")
    assert base is not None
    base_headers, _ = shape(base)
    used = _used_columns(configs, varied, set(base_headers), session)

    start_row = data.config.sampling_start_row
    for dataset_id in axis["values"]:
        dataset = session.get(Dataset, dataset_id)
        if not dataset:
            fail(f"Dataset {dataset_id} not found")
        assert dataset is not None
        headers, row_count = shape(dataset)
        if data.config.sampling_type == "range" and start_row and start_row > row_count:
            fail(
                f"Dataset '{dataset.name}' has {row_count} rows: "
                f"the range starting at row {start_row} would leave it empty"
            )
        if dataset_id == data.config.dataset_id:
            continue

        column_map = column_map_of(axis, dataset_id)
        if unknown := sorted(set(column_map) - set(base_headers)):
            fail(f"'{base.name}' has no column {', '.join(unknown)}")
        if absent := sorted(set(column_map.values()) - set(headers)):
            fail(f"Dataset '{dataset.name}' has no column {', '.join(absent)}")
        # A column read under another name is no longer there under its own
        taken = set(column_map.values())
        if missing := sorted(
            c
            for c in used
            if column_map.get(c, c) not in headers or (c not in column_map and c in taken)
        ):
            fail(
                f"Dataset '{dataset.name}' has no column for {', '.join(missing)}: "
                "choose which of its columns stands for each"
            )


def _used_columns(
    configs: dict[str, dict],
    varied: dict[str, dict[str, list]],
    base_headers: set[str],
    session: Session,
) -> set[str]:
    """Columns of the base dataset the batch's active steps read.

    A step with input mappings reads the columns they name. One without reads the
    whole row: its prompts' variables that are columns of the dataset.
    """
    used: set[str] = set()
    for step, config in configs.items():
        if not config or not config.get("is_active", True):
            continue
        mappings = [m for m in config.get("input_mappings") or [] if isinstance(m, dict)]
        used |= {
            m["sourceColumn"]
            for m in mappings
            if m.get("source") == "dataset" and m.get("sourceColumn")
        }
        if mappings:
            continue
        agent = session.get(Agent, agent_id_of(step))
        if not agent or agent.kind == AGGREGATOR:
            continue
        version_ids = [
            *varied.get(step, {}).get("prompt_version_id", []),
            config.get("prompt_version_id") or agent.default_prompt_version_id,
        ]
        for version_id in version_ids:
            version = session.get(PromptVersion, int(version_id)) if version_id else None
            if version:
                used |= prompt_variable_names(version.variables) & base_headers
    return used


# ---------------------------------------------------------------------------
# Response builder
# ---------------------------------------------------------------------------


def _build_batch_responses(
    batches: list[Batch], session: Session
) -> list[BatchResponse]:
    """Fully-populated BatchResponses, with a fixed number of queries."""
    experiments_of = grouped_by(
        session,
        Experiment,
        Experiment.batch_id,
        [b.id for b in batches if b.id is not None],
        col(Experiment.id),
    )
    experiments = [e for batch in batches for e in experiments_of[batch.id]]
    executions_of = grouped_by(
        session,
        ExperimentExecution,
        ExperimentExecution.experiment_id,
        [e.id for e in experiments if e.id is not None],
        col(ExperimentExecution.started_at).desc(),
    )

    # The agents each experiment's latest execution ran, in order
    latest_ids = [found[0].id for found in executions_of.values() if found]
    agent_names_of: dict[int, list[str]] = defaultdict(list)
    if latest_ids:
        for execution_id, name in session.exec(
            select(
                AgentExecutionSnapshot.execution_id,
                AgentExecutionSnapshot.agent_name_snapshot,
            )
            .where(col(AgentExecutionSnapshot.execution_id).in_(latest_ids))
            .order_by(col(AgentExecutionSnapshot.execution_order))
        ).all():
            agent_names_of[execution_id].append(name)

    bases = by_id(session, Experiment, (b.base_experiment_id for b in batches))
    datasets = by_id(session, Dataset, (e.dataset_id for e in experiments))
    labels = _preload_labels(batches, experiments, session)
    authors = people(session, (b.created_by for b in batches))

    return [
        _batch_response(
            batch,
            labels,
            experiments=experiments_of[batch.id],
            base=bases.get(batch.base_experiment_id),
            author=authors.get(batch.created_by),
            datasets=[
                datasets[dataset_id]
                for dataset_id in dict.fromkeys(e.dataset_id for e in experiments_of[batch.id])
                if dataset_id in datasets
            ],
            executions_of=executions_of,
            agent_names_of=agent_names_of,
        )
        for batch in batches
    ]


def _build_batch_response(batch: Batch, session: Session) -> BatchResponse:
    return _build_batch_responses([batch], session)[0]


def _preload_labels(
    batches: list[Batch], experiments: list[Experiment], session: Session
) -> _Labels:
    """The labels of the batches, with every row they name loaded in a few queries."""
    agent_ids: set[int] = set()
    model_ids: set[int] = set()
    version_ids: set[int] = set()
    dataset_ids: set[int] = set()

    def note(step: str, field: str, value: object) -> None:
        if step == DATASET_AXIS:
            if value is not None:
                dataset_ids.add(int(value))
            return
        agent_ids.add(agent_id_of(step))
        if value is None:
            return
        if field == "model_id":
            model_ids.add(int(value))
        elif field == "prompt_version_id":
            version_ids.add(int(value))

    for batch in batches:
        for variation in json.loads(batch.variations or "[]"):
            for value in variation["values"]:
                note(variation_step(variation), variation["field"], value)
    for experiment in experiments:
        for step, fields in parse_point(experiment.variant).items():
            for field, value in fields.items():
                note(step, field, value)

    labels = _Labels(session)
    labels.preload(Agent, agent_ids)
    labels.preload(Model, model_ids)
    labels.preload(PromptVersion, version_ids)
    labels.preload(Dataset, dataset_ids)
    versions = [labels.get(PromptVersion, i) for i in version_ids]
    labels.preload(Prompt, (v.prompt_id for v in versions if v is not None))
    return labels


def _axis_agent_id(variation: dict) -> int | None:
    """Agent whose step an axis varies; None for the dataset axis."""
    return None if is_dataset_axis(variation) else agent_id_of(variation_step(variation))


def _batch_response(
    batch: Batch,
    labels: _Labels,
    *,
    experiments: list[Experiment],
    base: Experiment | None,
    author: PersonResponse | None,
    datasets: list[Dataset],
    executions_of: dict[int, list[ExperimentExecution]],
    agent_names_of: dict[int, list[str]],
) -> BatchResponse:
    variations = json.loads(batch.variations or "[]")

    axis_responses = [
        VariationResponse(
            step_key=variation_step(v),
            agent_id=_axis_agent_id(v),
            agent_name=_agent_name(variation_step(v), labels),
            field=v["field"],
            values=[
                VariationValueResponse(
                    value=value,
                    label=_value_label(v["field"], value, labels),
                    column_map=column_map_of(v, int(value)) or None
                    if is_dataset_axis(v)
                    else None,
                )
                for value in v["values"]
            ],
        )
        for v in variations
    ]

    experiment_responses = []
    earlier_executions: list[ExperimentExecution] = []
    for experiment in experiments:
        point = parse_point(experiment.variant)
        coordinates = [
            VariantCoordinate(
                step_key=variation_step(v),
                agent_id=_axis_agent_id(v),
                field=v["field"],
                value=point[variation_step(v)][v["field"]],
                label=_value_label(
                    v["field"], point[variation_step(v)][v["field"]], labels
                ),
            )
            for v in variations
            if v["field"] in point.get(variation_step(v), {})
        ]
        executions = executions_of[experiment.id]
        execution = executions[0] if executions else None
        earlier_executions.extend(executions[1:])
        # The latest execution may have failed or be running again: analyses
        # work from the latest one that completed
        last_completed = next((e for e in executions if e.status == "completed"), None)

        agent_names = agent_names_of[execution.id] if execution else []

        experiment_responses.append(
            BatchExperimentResponse(
                id=int(experiment.id) if experiment.id is not None else 0,
                name=experiment.name,
                status=experiment.status,
                coordinates=coordinates,
                created_at=experiment.created_at,
                execution_id=execution.id if execution else None,
                execution_status=execution.status if execution else None,
                last_completed_execution_id=last_completed.id if last_completed else None,
                started_at=execution.started_at if execution else None,
                completed_at=execution.completed_at if execution else None,
                row_count=execution_row_count(execution) if execution else None,
                agent_names=agent_names,
                **latest_figures(executions),
            )
        )

    statuses = [e.status for e in experiments]
    tokens = [e.total_tokens for e in experiment_responses if e.total_tokens is not None]
    costs = [
        e.total_cost_usd for e in experiment_responses if e.total_cost_usd is not None
    ]
    return BatchResponse(
        id=int(batch.id) if batch.id is not None else 0,
        name=batch.name,
        description=batch.description,
        created_at=batch.created_at,
        author=author,
        base_experiment_id=base.id if base else None,
        base_experiment_name=base.name if base else None,
        # A batch that varies the dataset names them all, and links to none
        dataset_id=datasets[0].id if len(datasets) == 1 else None,
        dataset_name=", ".join(d.name for d in datasets) or None,
        variations=axis_responses,
        status=batch_status(statuses),
        counts=dict(Counter(statuses)),
        execution_count=sum(e.execution_count for e in experiment_responses),
        earlier_execution_statuses=[
            e.status
            for e in sorted(
                earlier_executions, key=lambda e: e.started_at, reverse=True
            )
        ],
        total_tokens=sum(tokens) if tokens else None,
        total_cost_usd=sum(costs) if costs else None,
        experiments=experiment_responses,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/batches", response_model=list[BatchResponse])
def list_batches(session: SessionDep):
    """Get all batches, newest first."""
    batches = session.exec(select(Batch).order_by(col(Batch.created_at).desc())).all()
    return _build_batch_responses(list(batches), session)


@router.post("/batches", response_model=BatchResponse, status_code=201)
def create_batch(
    data: BatchCreate, session: SessionDep
):
    """Create one experiment per point of the variations' grid, and start them all."""
    try:
        variations = normalize_variations([v.model_dump() for v in data.variations])
    except VariationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # The base configuration is one of the runs, unless it is an experiment that
    # already exists and the caller asked not to repeat it
    points = expand_variations(variations)
    if data.skip_base_point and data.base_experiment_id:
        base_values = _base_values(data, variations, session)
        points = [p for p in points if not is_base_point(p, base_values)]
    _validate_batch(data, variations, len(points), session)

    batch = Batch(
        name=data.name.strip(),
        description=data.description,
        base_experiment_id=data.base_experiment_id,
        # One random sample for the whole batch: the runs differ only by what varies
        sampling_seed=new_sampling_seed(data.config.sampling_seed)
        if data.config.sampling_type == "random"
        else None,
        variations=json.dumps(variations),
    )
    session.add(batch)
    session.flush()

    base = ExperimentCreate(
        name=batch.name,
        description=data.description,
        dataset_id=data.config.dataset_id,
        agent_configurations=data.config.agent_configurations,
        sampling_type=data.config.sampling_type,
        sampling_size=data.config.sampling_size,
        sampling_start_row=data.config.sampling_start_row,
        sampling_end_row=data.config.sampling_end_row,
        column_map=data.config.column_map,
    )
    dataset_axis = next((v for v in variations if is_dataset_axis(v)), None)
    multi_step = (
        len({variation_step(v) for v in variations if not is_dataset_axis(v)}) > 1
    )

    labels = _Labels(session)
    experiment_ids = []
    for point in points:
        parts = []
        for variation in variations:
            step = variation_step(variation)
            value = point[step][variation["field"]]
            label = _value_label(variation["field"], value, labels)
            parts.append(
                f"{_agent_name(step, labels)}: {label}"
                if multi_step and not is_dataset_axis(variation)
                else label
            )
        dataset_id = point.get(DATASET_AXIS, {}).get(DATASET_FIELD, base.dataset_id)
        try:
            experiment = add_experiment(
                session,
                base.model_copy(
                    update={
                        "dataset_id": dataset_id,
                        # The base dataset is read as the base configuration says
                        "column_map": column_map_of(dataset_axis, dataset_id)
                        if dataset_axis and dataset_id != base.dataset_id
                        else base.column_map,
                    }
                ),
                name=f"{batch.name} · {variant_label(parts)}",
                agent_overrides={
                    step: fields for step, fields in point.items() if step != DATASET_AXIS
                },
                batch_id=batch.id,
                variant=serialize_point(point),
            )
        except ExperimentConfigError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        experiment_ids.append(int(experiment.id) if experiment.id is not None else 0)
    session.commit()

    workspace_id = current_workspace_id(session)
    for experiment_id in experiment_ids:
        try:
            async_jobs.start_experiment(
                experiment_id, workspace_id, launched_by=current_user_id(session)
            )
        except Exception:
            logger.exception("Failed to start experiment %s", experiment_id)
    logger.info("Batch %s dispatched (%d experiments)", batch.id, len(experiment_ids))

    session.refresh(batch)
    return _build_batch_response(batch, session)


@router.get("/batches/{batch_id}", response_model=BatchResponse)
def get_batch(batch_id: int, session: SessionDep):
    batch = session.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _build_batch_response(batch, session)


@router.post("/batches/{batch_id}/cancel", response_model=BatchCancelResponse)
def cancel_batch(batch_id: int, session: SessionDep):
    """Cancel every experiment of the batch that is running or waiting to run."""
    batch = session.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    experiments = session.exec(
        select(Experiment).where(Experiment.batch_id == batch_id)
    ).all()
    cancelled = sum(
        async_jobs.cancel_experiment(int(e.id)) for e in experiments if e.id is not None
    )
    return BatchCancelResponse(batch_id=batch_id, cancelled=cancelled)


@router.post("/batches/{batch_id}/rerun", response_model=BatchRerunResponse)
def rerun_batch(batch_id: int, session: SessionDep):
    """Run again every experiment of the batch that is not running.

    Each one gets a new execution with its own configuration, and the batch's
    sample, so the variants stay comparable. Running and queued experiments are left
    alone: restarting a running one would cancel its current run.
    """
    batch = session.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    experiments = session.exec(
        select(Experiment).where(Experiment.batch_id == batch_id)
    ).all()

    started = 0
    skipped = 0
    workspace_id = current_workspace_id(session)
    for experiment in experiments:
        if experiment.id is None:
            continue
        if experiment.status in ("running", "queued"):
            skipped += 1
            continue
        try:
            async_jobs.start_experiment(
                int(experiment.id), workspace_id, launched_by=current_user_id(session)
            )
            started += 1
        except Exception:
            logger.exception("Failed to start experiment %s", experiment.id)
    logger.info("Batch %s re-run (%d experiments)", batch_id, started)
    return BatchRerunResponse(batch_id=batch_id, started=started, skipped=skipped)


@router.delete("/batches/{batch_id}", status_code=204)
def delete_batch(batch_id: int, session: SessionDep):
    """Delete the batch; its experiments stay, as ordinary experiments."""
    batch = session.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    for experiment in session.exec(
        select(Experiment).where(Experiment.batch_id == batch_id)
    ).all():
        experiment.batch_id = None
        experiment.variant = None
        session.add(experiment)

    clear_item_links(session, "batch", batch_id)
    session.delete(batch)
    session.commit()
