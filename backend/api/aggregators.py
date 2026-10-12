"""
Helpers for configuring aggregators: checking formulas, previewing them on the
rows of a past execution, and suggesting the paths an agent's outputs contain.
"""

import json
from collections import defaultdict

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, col, select

from analysis import result_rows
from auth.workspaces import requires
from core.formula import check_outputs, free_variables, name_errors
from core.json_output import list_paths, parse_json_output, scalar_paths
from core.orchestrator import AGGREGATOR, AgentConfig, run_aggregator
from db import SessionDep
from results_files import results_path
from schemas.aggregators import (
    AgentOutputPaths,
    AggregatorPreviewRequest,
    AggregatorPreviewResponse,
    AggregatorPreviewRow,
    FormulaCheckRequest,
    FormulaCheckResponse,
)
from tables import Agent, AgentExecutionSnapshot, Experiment, ExperimentExecution

router = APIRouter(tags=["aggregators"])

# Rows evaluated by a preview
PREVIEW_ROWS = 5
# Executions and rows scanned to suggest output paths
PATH_SCAN_EXECUTIONS = 5
PATH_SCAN_ROWS = 50


def _load_results(execution: ExperimentExecution) -> dict | None:
    path = results_path(execution)
    if path is None or not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _executions_with(
    session: Session, agent_ids: set[int], versions: dict[int, int] | None = None
):
    """
    Completed executions that ran every one of these agents, newest first.

    ``versions`` keeps only the executions where these agents ran with these
    prompt versions: another version may answer in another shape.
    """
    executions = session.exec(
        select(ExperimentExecution)
        .where(
            ExperimentExecution.status == "completed",
            col(ExperimentExecution.results_file_path).is_not(None),
        )
        .order_by(col(ExperimentExecution.started_at).desc())
    ).all()
    snapshots_of: dict[int, list] = defaultdict(list)
    if executions:
        for snapshot in session.exec(
            select(
                AgentExecutionSnapshot.execution_id,
                AgentExecutionSnapshot.agent_id,
                AgentExecutionSnapshot.agent_name_snapshot,
                AgentExecutionSnapshot.prompt_version_id,
            ).where(
                col(AgentExecutionSnapshot.execution_id).in_(
                    [e.id for e in executions]
                )
            )
        ).all():
            snapshots_of[snapshot.execution_id].append(snapshot)
    for execution in executions:
        snapshots = snapshots_of[execution.id]
        names = {s.agent_id: s.agent_name_snapshot for s in snapshots}
        if not agent_ids <= names.keys():
            continue
        ran_with = {s.agent_id: s.prompt_version_id for s in snapshots}
        if all(ran_with.get(a) == v for a, v in (versions or {}).items()):
            yield execution, names


@router.post("/aggregators/check", response_model=FormulaCheckResponse)
@requires("viewer")
def check_formulas(request: FormulaCheckRequest):
    """Errors of each formula, and the variables they leave to map."""
    formulas = [f.model_dump() for f in request.formulas]
    return FormulaCheckResponse(
        errors=check_outputs(formulas),
        name_invalid=[e is not None for e in name_errors(formulas)],
        variables=free_variables(formulas),
    )


@router.post("/aggregators/preview", response_model=AggregatorPreviewResponse)
@requires("viewer")
def preview_aggregator(
    request: AggregatorPreviewRequest,
    session: SessionDep,
):
    """
    Evaluate formulas on the first rows of the latest execution that ran every
    agent they read, using what those agents actually returned.
    """
    formulas = [f.model_dump() for f in request.formulas]
    variables = set(free_variables(formulas))
    source_ids = {
        m["sourceAgentId"]
        for m in request.input_mappings
        if m.get("variable") in variables
        and m.get("source") == "agent"
        and isinstance(m.get("sourceAgentId"), int)
    }
    if not source_ids:
        return AggregatorPreviewResponse()

    # Rows where the agents ran with the versions the experiment uses, else any
    versions = {
        a: v for a, v in request.prompt_versions.items() if a in source_ids and v
    }
    matching = _executions_with(session, source_ids, versions)
    first = next(matching, None)
    versions_match = first is not None
    if first is None:
        first = next(_executions_with(session, source_ids), None)
    candidates = [first] if first else []

    for execution, names in candidates:
        results = _load_results(execution)
        if results is None:
            continue
        ids_by_name = {name: agent_id for agent_id, name in names.items()}
        aggregator = AgentConfig(
            name="Preview",
            system_prompt=None,
            user_prompt=None,
            variables=[],
            model="",
            provider="",
            kind=AGGREGATOR,
            formulas=formulas,
            input_mappings=request.input_mappings,
        )
        rows = []
        for row in result_rows(results)[:PREVIEW_ROWS]:
            outputs = {
                ids_by_name[a.get("name")]: a.get("output")
                for a in row.get("agents") or []
                if a.get("name") in ids_by_name and not a.get("error")
            }
            trace = run_aggregator(
                aggregator, row.get("input_data") or {}, outputs, names
            )
            rows.append(
                AggregatorPreviewRow(
                    row_index=row.get("row_index"),
                    inputs=trace.inputs or {},
                    output=json.loads(trace.output) if trace.output else None,
                    error=trace.error,
                )
            )
        experiment = session.get(Experiment, execution.experiment_id)
        return AggregatorPreviewResponse(
            execution_id=execution.id,
            experiment_name=experiment.name if experiment else None,
            versions_match=versions_match,
            rows=rows,
        )
    return AggregatorPreviewResponse()


@router.get("/agents/{agent_id}/output-paths", response_model=AgentOutputPaths)
def get_agent_output_paths(
    agent_id: int,
    session: SessionDep,
    prompt_version_id: int | None = None,
):
    """
    Paths to values seen in the agent's outputs, in recent executions; only
    those run with ``prompt_version_id`` when given.
    """
    if not session.get(Agent, agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")

    paths: dict[str, None] = {}
    lists: dict[str, None] = {}
    scanned = 0
    versions = {agent_id: prompt_version_id} if prompt_version_id else None
    for execution, names in _executions_with(session, {agent_id}, versions):
        results = _load_results(execution)
        if results is None:
            continue
        for row in result_rows(results)[:PATH_SCAN_ROWS]:
            for agent in row.get("agents") or []:
                if agent.get("name") == names[agent_id] and not agent.get("error"):
                    output = parse_json_output(agent.get("output"))
                    paths.update(dict.fromkeys(p for p in scalar_paths(output) if p))
                    lists.update(dict.fromkeys(list_paths(output)))
        scanned += 1
        if scanned >= PATH_SCAN_EXECUTIONS:
            break
    return AgentOutputPaths(
        agent_id=agent_id, paths=list(paths), list_paths=list(lists)
    )
