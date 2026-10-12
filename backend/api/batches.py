import json
import logging
from collections import Counter, defaultdict
from collections.abc import Iterable

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, col, select

import async_jobs
from batch_utils import (
    MAX_BATCH_EXPERIMENTS,
    VariationError,
    batch_status,
    expand_variations,
    format_temperature,
    is_base_point,
    normalize_variations,
    parse_point,
    prompt_variable_names,
    serialize_point,
    unmapped_variables,
    variant_label,
)
from core.orchestrator import AGGREGATOR
from db import SessionDep
from execution_stats import latest_figures
from experiment_utils import ExperimentConfigError, add_experiment, new_sampling_seed
from loading import by_id, grouped_by
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
from workspace_scope import current_workspace_id

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
    if field == "model_id":
        model = labels.get(Model, int(value))
        return model.name if model else f"model {value}"
    version = labels.get(PromptVersion, int(value))
    if version is None:
        return f"prompt {value}"
    prompt = labels.get(Prompt, version.prompt_id)
    prompt_name = prompt.name if prompt else "Prompt"
    return f"{prompt_name} v{version.version}"


def _agent_name(agent_id: int, labels: _Labels) -> str:
    agent = labels.get(Agent, agent_id)
    return agent.name if agent else f"agent {agent_id}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _base_values(
    data: BatchCreate, variations: list[dict], session: Session
) -> dict[tuple[int, str], int | float | None]:
    """The value each varied field has in the base configuration."""
    values: dict[tuple[int, str], int | float | None] = {}
    for variation in variations:
        agent_id, field = variation["agent_id"], variation["field"]
        config = data.config.agent_configurations.get(str(agent_id)) or {}
        value = config.get(field)
        if value is None and field != "temperature":
            agent = session.get(Agent, agent_id)
            default = None
            if agent:
                default = (
                    agent.default_model_id
                    if field == "model_id"
                    else agent.default_prompt_version_id
                )
            value = default
        values[(agent_id, field)] = value
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

    if total < 1:
        fail("Nothing to run: the only experiment would repeat the base experiment")
    if total > MAX_BATCH_EXPERIMENTS:
        fail(
            f"This batch would create {total} experiments "
            f"(the maximum is {MAX_BATCH_EXPERIMENTS})"
        )

    configs = data.config.agent_configurations
    varied: dict[int, dict[str, list]] = {}
    for variation in variations:
        varied.setdefault(variation["agent_id"], {})[variation["field"]] = variation[
            "values"
        ]

    # The base configuration: every active agent must end up with a prompt and a
    # model, otherwise the experiment would silently skip it
    active_agents = 0
    for agent_id_str, config in configs.items():
        if not config or not config.get("is_active", True):
            continue
        agent = session.get(Agent, int(agent_id_str))
        if not agent:
            continue
        active_agents += 1
        if agent.kind == AGGREGATOR:
            # Computed from formulas: no prompt and no model
            continue
        axes = varied.get(agent.id, {})
        if not (
            "prompt_version_id" in axes
            or config.get("prompt_version_id")
            or agent.default_prompt_version_id
        ):
            fail(f"Agent '{agent.name}' has no prompt version")
        if not (
            "model_id" in axes or config.get("model_id") or agent.default_model_id
        ):
            fail(f"Agent '{agent.name}' has no model")
    if active_agents == 0:
        fail("The batch has no active agent")

    for agent_id, axes in varied.items():
        agent = session.get(Agent, agent_id)
        config = configs.get(str(agent_id))
        if not agent or not config or not config.get("is_active", True):
            fail(f"Agent {agent_id} is not an active agent of the batch")
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
                    f"Agent '{agent.name}': prompt "
                    f"'{_value_label('prompt_version_id', version_id, _Labels(session))}' "
                    f"needs variables with no input mapping: "
                    f"{', '.join(sorted(missing))}"
                )


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
    datasets = by_id(
        session,
        Dataset,
        (experiments_of[b.id][0].dataset_id for b in batches if experiments_of[b.id]),
    )
    labels = _preload_labels(batches, experiments, session)

    return [
        _batch_response(
            batch,
            labels,
            experiments=experiments_of[batch.id],
            base=bases.get(batch.base_experiment_id),
            dataset=datasets.get(experiments_of[batch.id][0].dataset_id)
            if experiments_of[batch.id]
            else None,
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

    def note(agent_id: int, field: str, value: object) -> None:
        agent_ids.add(agent_id)
        if value is None:
            return
        if field == "model_id":
            model_ids.add(int(value))
        elif field == "prompt_version_id":
            version_ids.add(int(value))

    for batch in batches:
        for variation in json.loads(batch.variations or "[]"):
            for value in variation["values"]:
                note(variation["agent_id"], variation["field"], value)
    for experiment in experiments:
        for agent_id, fields in parse_point(experiment.variant).items():
            for field, value in fields.items():
                note(agent_id, field, value)

    labels = _Labels(session)
    labels.preload(Agent, agent_ids)
    labels.preload(Model, model_ids)
    labels.preload(PromptVersion, version_ids)
    versions = [labels.get(PromptVersion, i) for i in version_ids]
    labels.preload(Prompt, (v.prompt_id for v in versions if v is not None))
    return labels


def _batch_response(
    batch: Batch,
    labels: _Labels,
    *,
    experiments: list[Experiment],
    base: Experiment | None,
    dataset: Dataset | None,
    executions_of: dict[int, list[ExperimentExecution]],
    agent_names_of: dict[int, list[str]],
) -> BatchResponse:
    variations = json.loads(batch.variations or "[]")

    axis_responses = [
        VariationResponse(
            agent_id=v["agent_id"],
            agent_name=_agent_name(v["agent_id"], labels),
            field=v["field"],
            values=[
                VariationValueResponse(
                    value=value, label=_value_label(v["field"], value, labels)
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
                agent_id=v["agent_id"],
                field=v["field"],
                value=point[v["agent_id"]][v["field"]],
                label=_value_label(v["field"], point[v["agent_id"]][v["field"]], labels),
            )
            for v in variations
            if v["field"] in point.get(v["agent_id"], {})
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
        base_experiment_id=base.id if base else None,
        base_experiment_name=base.name if base else None,
        dataset_id=dataset.id if dataset else None,
        dataset_name=dataset.name if dataset else None,
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
    )
    multi_agent = len({v["agent_id"] for v in variations}) > 1

    labels = _Labels(session)
    experiment_ids = []
    for point in points:
        parts = []
        for variation in variations:
            value = point[variation["agent_id"]][variation["field"]]
            label = _value_label(variation["field"], value, labels)
            parts.append(
                f"{_agent_name(variation['agent_id'], labels)}: {label}"
                if multi_agent
                else label
            )
        try:
            experiment = add_experiment(
                session,
                base,
                name=f"{batch.name} · {variant_label(parts)}",
                agent_overrides=point,
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
            async_jobs.start_experiment(experiment_id, workspace_id)
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
            async_jobs.start_experiment(int(experiment.id), workspace_id)
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
