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
from core.steps import agent_id_of, mapping_source
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
    session: Session, steps: set[str], versions: dict[str, int] | None = None
):
    """
    Completed executions that ran a step for each of these ones, newest first.

    A step that an execution did not run under that key is looked for among the
    other steps of its agent: what an agent answers does not depend on how many
    times it runs. ``versions`` keeps only the executions where these steps ran
    with these prompt versions: another version may answer in another shape.

    Yields the execution, the name of each of its steps by key, and the key of
    the step standing for each of the ones asked.
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
                AgentExecutionSnapshot.step_key,
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
        ran = {
            s.step_key or str(s.agent_id): s
            for s in snapshots_of[execution.id]
            if s.step_key or s.agent_id is not None
        }
        standing_for: dict[str, str] = {}
        for step in steps:
            # The step itself first, then the other steps of its agent; with a
            # version asked, the first of them that ran with it
            same_agent = [step] if step in ran else []
            same_agent += [
                k
                for k, s in ran.items()
                if k != step and s.agent_id == agent_id_of(step)
            ]
            version = (versions or {}).get(step)
            found = next(
                (
                    k
                    for k in same_agent
                    if version is None or ran[k].prompt_version_id == version
                ),
                None,
            )
            if found is None:
                break
            standing_for[step] = found
        else:
            names = {key: s.agent_name_snapshot for key, s in ran.items()}
            yield execution, names, standing_for


def _is_step(step: str) -> bool:
    try:
        agent_id_of(step)
    except ValueError:
        return False
    return True


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
    source_steps = {
        step
        for m in request.input_mappings
        if m.get("variable") in variables
        and m.get("source") == "agent"
        and (step := mapping_source(m)) is not None
        and _is_step(step)
    }
    if not source_steps:
        return AggregatorPreviewResponse()

    # Rows where the agents ran with the versions the experiment uses, else any
    versions = {
        a: v for a, v in request.prompt_versions.items() if a in source_steps and v
    }
    matching = _executions_with(session, source_steps, versions)
    first = next(matching, None)
    versions_match = first is not None
    if first is None:
        first = next(_executions_with(session, source_steps), None)
    candidates = [first] if first else []

    for execution, ran_names, standing_for in candidates:
        names = {step: ran_names[key] for step, key in standing_for.items()}
        steps_named: dict[str, list[str]] = defaultdict(list)
        for step, name in names.items():
            steps_named[name].append(step)
        results = _load_results(execution)
        if results is None:
            continue
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
                step: a.get("output")
                for a in row.get("agents") or []
                if not a.get("error")
                for step in steps_named.get(a.get("name"), [])
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
    step = str(agent_id)
    versions = {step: prompt_version_id} if prompt_version_id else None
    for execution, names, standing_for in _executions_with(session, {step}, versions):
        results = _load_results(execution)
        if results is None:
            continue
        for row in result_rows(results)[:PATH_SCAN_ROWS]:
            for agent in row.get("agents") or []:
                if agent.get("name") == names[standing_for[step]] and not agent.get(
                    "error"
                ):
                    output = parse_json_output(agent.get("output"))
                    paths.update(dict.fromkeys(p for p in scalar_paths(output) if p))
                    lists.update(dict.fromkeys(list_paths(output)))
        scanned += 1
        if scanned >= PATH_SCAN_EXECUTIONS:
            break
    return AgentOutputPaths(
        agent_id=agent_id, paths=list(paths), list_paths=list(lists)
    )
