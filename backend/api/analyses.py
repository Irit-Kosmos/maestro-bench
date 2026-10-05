import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select

from analysis import METRICS, AnalysisConfig, RunInput, result_rows
from analysis.compute import comparison_warnings, compute_run, validate_config
from auth.workspaces import requires
from core.json_output import parse_json_output, scalar_paths
from db import get_session
from references import missing_ids
from results_files import execution_row_count, results_path
from schemas.analyses import (
    AgentFields,
    AgentRowOutput,
    AnalysisComputeRequest,
    AnalysisConfigSchema,
    AnalysisCreate,
    AnalysisResponse,
    AnalysisResultResponse,
    AnalysisRunRef,
    AnalysisUpdate,
    AvailableExecution,
    ExecutionFields,
    ExecutionRow,
    MetricInfo,
    RunResultResponse,
)
from schemas.tags import TagResponse
from tables import (
    AgentExecutionSnapshot,
    Analysis,
    Experiment,
    ExperimentExecution,
    Tag,
)
from tag_utils import clear_item_tags, item_tags, set_item_tags, tags_by_item

router = APIRouter(tags=["analyses"])

# Rows scanned to suggest output paths; outputs usually share one shape
FIELD_SCAN_ROWS = 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_response(analysis: Analysis, tags: list[Tag]) -> AnalysisResponse:
    return AnalysisResponse(
        id=int(analysis.id) if analysis.id is not None else 0,
        name=analysis.name,
        description=analysis.description,
        config=AnalysisConfigSchema.model_validate_json(analysis.config),
        runs=[AnalysisRunRef.model_validate(r) for r in json.loads(analysis.runs)],
        tags=[TagResponse.model_validate(t) for t in tags],
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
    )


def _to_config(schema: AnalysisConfigSchema) -> AnalysisConfig:
    return AnalysisConfig(**schema.model_dump())


def _check_runs(refs: list[AnalysisRunRef], session: Session) -> None:
    """Every run an analysis compares must be an execution of the workspace."""
    missing = missing_ids(
        session, ExperimentExecution, [ref.execution_id for ref in refs]
    )
    if missing:
        raise HTTPException(status_code=422, detail=f"Unknown executions: {missing}")


def _check_config(schema: AnalysisConfigSchema) -> None:
    try:
        validate_config(_to_config(schema))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


def _load_results(execution: ExperimentExecution) -> dict | None:
    path = results_path(execution)
    if path is None or not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _default_label(experiment: Experiment | None, results: dict, agent: str) -> str:
    name = experiment.name if experiment else "Unknown experiment"
    agents = (results.get("configuration_used") or {}).get("agents") or []
    model = next((a["model_name"] for a in agents if a["agent_name"] == agent), None)
    return f"{name} · {model}" if model else name


def _compute(
    config: AnalysisConfigSchema, refs: list[AnalysisRunRef], session: Session
) -> AnalysisResultResponse:
    _check_config(config)
    analysis_config = _to_config(config)

    responses: list[RunResultResponse] = []
    inputs: list[RunInput] = []
    for ref in refs:
        execution = session.get(ExperimentExecution, ref.execution_id)
        if not execution:
            responses.append(
                RunResultResponse(
                    execution_id=ref.execution_id,
                    agent_name=ref.agent_name,
                    label=ref.label or f"Execution {ref.execution_id}",
                    status="missing",
                    error="Execution not found",
                )
            )
            continue

        experiment = session.get(Experiment, execution.experiment_id)
        results = _load_results(execution)
        if results is None:
            responses.append(
                RunResultResponse(
                    execution_id=ref.execution_id,
                    agent_name=ref.agent_name,
                    label=ref.label or f"Execution {ref.execution_id}",
                    status="unavailable",
                    error="No results file for this execution",
                    experiment_id=execution.experiment_id,
                    experiment_name=experiment.name if experiment else None,
                )
            )
            continue

        run = RunInput(
            label=ref.label or _default_label(experiment, results, ref.agent_name),
            agent_name=ref.agent_name,
            rows=result_rows(results),
            execution_id=ref.execution_id,
            dataset=json.loads(execution.dataset_snapshot),
        )
        inputs.append(run)
        result = compute_run(analysis_config, run)
        responses.append(
            RunResultResponse(
                **_jsonable(asdict(result)),
                status="ok",
                coverage=result.coverage,
                experiment_id=execution.experiment_id,
                experiment_name=experiment.name if experiment else None,
            )
        )

    return AnalysisResultResponse(
        metrics=[_metric_info(key) for key in config.metrics],
        runs=responses,
        # Only the runs that could be computed are compared
        warnings=comparison_warnings(inputs),
    )


def _jsonable(data: dict) -> dict:
    """asdict() keeps enum members; turn them into their values."""
    return json.loads(json.dumps(data, default=str))


def _metric_info(key: str) -> MetricInfo:
    metric = METRICS[key]
    return MetricInfo(
        key=metric.key,
        label=metric.label,
        kind=metric.kind,
        description=metric.description,
        lower_is_better=metric.lower_is_better,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/analyses/metrics", response_model=list[MetricInfo])
def list_metrics():
    """Metrics available to analyses, grouped by kind."""
    return [_metric_info(key) for key in METRICS]


@router.get("/analyses/executions", response_model=list[AvailableExecution])
def list_available_executions(session: Annotated[Session, Depends(get_session)]):
    """Completed executions that have a results file, newest first."""
    executions = session.exec(
        select(ExperimentExecution)
        .where(
            ExperimentExecution.status == "completed",
            col(ExperimentExecution.results_file_path).is_not(None),
        )
        .order_by(col(ExperimentExecution.started_at).desc())
    ).all()

    available = []
    for execution in executions:
        experiment = session.get(Experiment, execution.experiment_id)
        snapshots = session.exec(
            select(AgentExecutionSnapshot)
            .where(AgentExecutionSnapshot.execution_id == execution.id)
            .order_by(AgentExecutionSnapshot.execution_order)
        ).all()
        dataset = json.loads(execution.dataset_snapshot or "{}")
        available.append(
            AvailableExecution(
                execution_id=int(execution.id) if execution.id is not None else 0,
                experiment_id=execution.experiment_id,
                experiment_name=experiment.name if experiment else "Unknown",
                dataset_name=dataset.get("name"),
                started_at=execution.started_at,
                completed_at=execution.completed_at,
                row_count=execution_row_count(execution),
                agents=[
                    {"name": s.agent_name_snapshot, "model": s.model_name_snapshot}
                    for s in snapshots
                ],
            )
        )
    return available


@router.get(
    "/executions/{execution_id}/analysis-fields", response_model=ExecutionFields
)
def get_execution_fields(
    execution_id: int, session: Annotated[Session, Depends(get_session)]
):
    """Dataset columns and agent output paths that an analysis can select."""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    results = _load_results(execution)
    if results is None:
        raise HTTPException(status_code=404, detail="No results file available")

    rows = result_rows(results)[:FIELD_SCAN_ROWS]
    columns: dict[str, None] = {}
    paths: dict[str, dict[str, None]] = {}
    for row in rows:
        columns.update(dict.fromkeys(row.get("input_data") or {}))
        for agent in row.get("agents") or []:
            agent_paths = paths.setdefault(agent.get("name"), {})
            output = parse_json_output(agent.get("output"))
            agent_paths.update(dict.fromkeys(scalar_paths(output)))

    configured = (results.get("configuration_used") or {}).get("agents") or []
    agents = [
        AgentFields(
            name=a["agent_name"],
            model=a.get("model_name"),
            execution_order=a.get("execution_order", i + 1),
            paths=list(paths.get(a["agent_name"], {})),
        )
        for i, a in enumerate(configured)
    ]
    # Results files without a configuration section: fall back to row contents
    if not agents:
        agents = [
            AgentFields(name=name, model=None, execution_order=i + 1, paths=list(p))
            for i, (name, p) in enumerate(paths.items())
        ]
    return ExecutionFields(
        execution_id=execution_id, columns=list(columns), agents=agents
    )


@router.get("/executions/{execution_id}/rows/{row_index}", response_model=ExecutionRow)
def get_execution_row(
    execution_id: int,
    row_index: int,
    session: Annotated[Session, Depends(get_session)],
):
    """One row of an execution, to look up a point of an analysis."""
    execution = session.get(ExperimentExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    results = _load_results(execution)
    if results is None:
        raise HTTPException(status_code=404, detail="No results file available")

    row = next(
        (r for r in result_rows(results) if r.get("row_index") == row_index), None
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Row not found")
    return ExecutionRow(
        row_index=row_index,
        input_data=row.get("input_data") or {},
        agents=[
            AgentRowOutput(
                name=agent.get("name"),
                kind=agent.get("kind") or "llm",
                inputs=agent.get("inputs"),
                output=parse_json_output(agent.get("output")),
                error=agent.get("error"),
            )
            for agent in row.get("agents") or []
        ],
        error=row.get("error"),
    )


@router.post("/analyses/compute", response_model=AnalysisResultResponse)
@requires("viewer")
def compute_unsaved_analysis(
    request: AnalysisComputeRequest,
    session: Annotated[Session, Depends(get_session)],
):
    """Compute an analysis without saving it (previews, scripts, notebooks)."""
    return _compute(request.config, request.runs, session)


@router.get("/analyses", response_model=list[AnalysisResponse])
def list_analyses(session: Annotated[Session, Depends(get_session)]):
    analyses = session.exec(
        select(Analysis).order_by(col(Analysis.updated_at).desc())
    ).all()
    tags = tags_by_item(session, "analysis", [a.id for a in analyses if a.id])
    return [_to_response(a, tags.get(a.id or 0, [])) for a in analyses]


@router.post("/analyses", response_model=AnalysisResponse, status_code=201)
def create_analysis(
    data: AnalysisCreate, session: Annotated[Session, Depends(get_session)]
):
    _check_config(data.config)
    _check_runs(data.runs, session)
    analysis = Analysis(
        name=data.name,
        description=data.description,
        config=data.config.model_dump_json(),
        runs=json.dumps([r.model_dump() for r in data.runs]),
    )
    session.add(analysis)
    session.flush()
    set_item_tags(session, "analysis", analysis.id or 0, data.tag_ids)
    session.commit()
    session.refresh(analysis)
    return _to_response(analysis, item_tags(session, "analysis", analysis.id or 0))


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: int, session: Annotated[Session, Depends(get_session)]):
    analysis = session.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _to_response(analysis, item_tags(session, "analysis", analysis_id))


@router.put("/analyses/{analysis_id}", response_model=AnalysisResponse)
def update_analysis(
    analysis_id: int,
    data: AnalysisUpdate,
    session: Annotated[Session, Depends(get_session)],
):
    analysis = session.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if data.name is not None:
        analysis.name = data.name
    if "description" in data.model_fields_set:
        analysis.description = data.description
    if data.config is not None:
        _check_config(data.config)
        analysis.config = data.config.model_dump_json()
    if data.runs is not None:
        _check_runs(data.runs, session)
        analysis.runs = json.dumps([r.model_dump() for r in data.runs])
    if data.tag_ids is not None:
        set_item_tags(session, "analysis", analysis_id, data.tag_ids)
    analysis.updated_at = datetime.now(UTC)

    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return _to_response(analysis, item_tags(session, "analysis", analysis_id))


@router.delete("/analyses/{analysis_id}")
def delete_analysis(
    analysis_id: int, session: Annotated[Session, Depends(get_session)]
):
    analysis = session.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    clear_item_tags(session, "analysis", analysis_id)
    session.delete(analysis)
    session.commit()
    return {"message": "Analysis deleted successfully"}


@router.get("/analyses/{analysis_id}/results", response_model=AnalysisResultResponse)
def get_analysis_results(
    analysis_id: int, session: Annotated[Session, Depends(get_session)]
):
    """Recompute the analysis from the executions' results files."""
    analysis = session.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    response = _to_response(analysis, [])
    return _compute(response.config, response.runs, session)
