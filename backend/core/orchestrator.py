"""
Sequential agent pipeline orchestrator.

Executes a list of agents in order, passing each agent's output
as context to subsequent agents. Collects per-agent traces
(prompts, responses, token usage, latency, cost).

Agents are LLM calls, or aggregators: formulas computed from other agents'
outputs, dataset columns and static values (see core.formula).
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any

from core.formula import FormulaError, coerce_input, evaluate_outputs, free_variables
from core.json_output import (
    MISSING,
    get_path,
    parse_json_output,
    strip_markdown_fences,
)
from core.llm import LLMResponse, call_llm
from core.prompt_renderer import build_messages

AGGREGATOR = "aggregator"


@dataclass
class AgentConfig:
    """Configuration for a single agent in the pipeline."""

    name: str
    team_name: str
    system_prompt: str | None
    user_prompt: str | None
    variables: list[str]  # variable names this agent expects
    model: str
    provider: str
    temperature: float = 0.0
    max_tokens: int | None = None
    execution_order: int = 1
    input_mappings: list[dict] | None = None
    agent_id: int | None = None
    kind: str = "llm"
    # Aggregators only: ordered [{"name", "formula"}]
    formulas: list[dict] | None = None
    # The workspace's own key for the provider, if it has one (None: the instance's).
    # Kept out of repr so it never reaches a log line.
    api_key: str | None = field(default=None, repr=False)
    key_id: str = "instance"


@dataclass
class AgentTrace:
    """Trace of a single agent execution."""

    agent_name: str
    model: str
    provider: str
    messages_sent: list[dict]
    output: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    error: str | None = None
    kind: str = "llm"
    # Aggregators only: the value each formula variable resolved to
    inputs: dict | None = None


@dataclass
class PipelineResult:
    """Result of running the full agent pipeline on one data row."""

    row_index: int
    input_data: dict  # Dataset row (column name -> value)
    # 0-based position of the row in the dataset file, stable across sampling
    dataset_row_id: int | None = None
    agent_traces: list[AgentTrace] = field(default_factory=list)
    final_output: str = ""
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage."""
        return {
            "row_index": self.row_index,
            "dataset_row_id": self.dataset_row_id,
            "input_data": {k: _safe_serialize(v) for k, v in self.input_data.items()},
            "agents": [
                {
                    "name": t.agent_name,
                    "kind": t.kind,
                    **({"inputs": t.inputs} if t.inputs is not None else {}),
                    "model": t.model,
                    "provider": t.provider,
                    "messages_sent": t.messages_sent,
                    "output": parse_json_output(t.output),
                    "tokens_in": t.tokens_in,
                    "tokens_out": t.tokens_out,
                    "cost_usd": t.cost_usd,
                    "latency_ms": round(t.latency_ms, 1),
                    "error": t.error,
                }
                for t in self.agent_traces
            ],
            "final_output": parse_json_output(self.final_output),
            "totals": {
                "tokens_in": self.total_tokens_in,
                "tokens_out": self.total_tokens_out,
                "cost_usd": self.total_cost_usd,
                "latency_ms": round(self.total_latency_ms, 1),
            },
            "error": self.error,
        }


def _safe_serialize(value):
    """Convert pandas/numpy types to JSON-safe Python types."""
    import math

    if hasattr(value, "item"):  # numpy scalar
        return value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _mapped_value(mapping: dict, row: dict, agent_outputs: dict) -> Any:
    """Value an input mapping points to, or MISSING when there is none."""
    source = mapping.get("source")
    if source == "dataset":
        column = mapping.get("sourceColumn")
        return row.get(column, MISSING) if column else MISSING
    if source == "agent":
        raw = agent_outputs.get(mapping.get("sourceAgentId"), MISSING)
        path = mapping.get("sourcePath") or ""
        if raw is MISSING or not path:
            return raw
        return get_path(parse_json_output(raw), path)
    if source == "static":
        return mapping.get("staticValue", MISSING)
    return MISSING


def _resolve_agent_context(
    agent: AgentConfig,
    shared_context: dict,
    row: dict,
    agent_outputs: dict,
) -> dict:
    """
    Build the variable context for a single LLM agent.

    If the agent has explicit input_mappings, use them to map dataset columns,
    previous agent outputs (whole, or a dotted path into their JSON), or static
    values to prompt variables. Otherwise fall back to the full shared context
    (dataset row + all previous agent outputs).
    """
    if not agent.input_mappings:
        return shared_context

    resolved: dict = {}
    for mapping in agent.input_mappings:
        variable = mapping.get("variable")
        if not variable or not mapping.get("source"):
            continue
        value = _mapped_value(mapping, row, agent_outputs)
        if value is MISSING:
            value = None
        elif isinstance(value, dict | list):
            value = json.dumps(value, ensure_ascii=False)
        resolved[variable] = value

    return resolved


def _aggregator_inputs(
    agent: AgentConfig, row: dict, agent_outputs: dict, agent_names: dict
) -> dict:
    """
    Values of an aggregator's formula variables.

    Strict: a variable without a mapping, or whose mapping leads nowhere or to
    something that is not a single value, raises FormulaError.
    """
    mappings = {m.get("variable"): m for m in agent.input_mappings or []}
    inputs: dict = {}
    for variable in free_variables(agent.formulas or []):
        mapping = mappings.get(variable)
        if not mapping or not mapping.get("source"):
            raise FormulaError(f'variable "{variable}" is not mapped')
        value = _mapped_value(mapping, row, agent_outputs)
        if value is MISSING:
            raise FormulaError(
                f'variable "{variable}": {_missing_reason(mapping, agent_names)}'
            )
        if mapping["source"] == "agent" and not mapping.get("sourcePath"):
            value = parse_json_output(value)
        try:
            inputs[variable] = coerce_input(value)
        except FormulaError as e:
            raise FormulaError(f'variable "{variable}" {e}') from e
    return inputs


def _missing_reason(mapping: dict, agent_names: dict) -> str:
    source = mapping.get("source")
    if source == "dataset":
        return f'column "{mapping.get("sourceColumn") or "?"}" not found'
    if source == "agent":
        agent_id = mapping.get("sourceAgentId")
        name = agent_names.get(agent_id)
        if name is None:
            return f"agent #{agent_id} has not run before this one"
        return f'path "{mapping.get("sourcePath")}" not found in the output of {name}'
    return "no value"


async def run_pipeline(
    agents: list[AgentConfig],
    row: dict,
    row_index: int = 0,
    dataset_row_id: int | None = None,
) -> PipelineResult:
    """
    Execute a sequential agent pipeline on a single dataset row.

    Each agent receives:
    - Explicit per-agent input mappings when configured, or
    - The full dataset row plus outputs from all previous agents
      as {{ AgentName_output }}

    Args:
        agents: Ordered list of agent configurations
        row: Dataset row (column name → value)
        row_index: 1-based position of this row in the processed sample
        dataset_row_id: 0-based position of this row in the dataset file

    Returns:
        PipelineResult with all agent traces and aggregated metrics
    """
    result = PipelineResult(
        row_index=row_index, input_data=row, dataset_row_id=dataset_row_id
    )

    # Shared context: starts with the row, accumulates agent outputs
    context = dict(row)

    # Raw agent outputs and names by agent id, for explicit mappings
    agent_outputs: dict = {}
    agent_names: dict = {}

    # Sort agents by execution_order
    sorted_agents = sorted(agents, key=lambda a: a.execution_order)

    for agent in sorted_agents:
        if agent.kind == AGGREGATOR:
            trace = run_aggregator(agent, row, agent_outputs, agent_names)
        else:
            # Resolve this agent's private variable context
            agent_context = _resolve_agent_context(agent, context, row, agent_outputs)
            trace = await _execute_agent(agent, agent_context)
        result.agent_traces.append(trace)

        # Accumulate totals
        result.total_tokens_in += trace.tokens_in
        result.total_tokens_out += trace.tokens_out
        result.total_cost_usd += trace.cost_usd
        result.total_latency_ms += trace.latency_ms

        if trace.error:
            result.error = f"Agent '{agent.name}' failed: {trace.error}"
            break

        # Make this agent's output available to subsequent agents
        # Convention: {{ AgentName_output }} (spaces replaced with underscores)
        safe_name = agent.name.replace(" ", "_")
        context[f"{safe_name}_output"] = trace.output

        # Also store by agent id for explicit input mappings
        if agent.agent_id is not None:
            agent_outputs[agent.agent_id] = trace.output
            agent_names[agent.agent_id] = agent.name

    # Final output = last successful agent's output
    if result.agent_traces:
        last_trace = result.agent_traces[-1]
        result.final_output = last_trace.output if not last_trace.error else ""

    return result


def run_aggregator(
    agent: AgentConfig, row: dict, agent_outputs: dict, agent_names: dict
) -> AgentTrace:
    """
    Compute an aggregator's formulas from what earlier agents returned.

    ``agent_outputs`` and ``agent_names`` are keyed by agent id; outputs are
    raw text or already parsed JSON.
    """
    started = time.perf_counter()
    inputs: dict | None = None
    try:
        inputs = _aggregator_inputs(agent, row, agent_outputs, agent_names)
        output = evaluate_outputs(agent.formulas or [], inputs)
        error = None
    except FormulaError as e:
        output, error = None, str(e)
    return AgentTrace(
        agent_name=agent.name,
        model="",
        provider="",
        messages_sent=[],
        output=json.dumps(output) if output is not None else "",
        latency_ms=(time.perf_counter() - started) * 1000,
        error=error,
        kind=AGGREGATOR,
        inputs=inputs or {},
    )


async def _execute_agent(agent: AgentConfig, context: dict) -> AgentTrace:
    """Execute a single agent with the current context."""
    try:
        messages = build_messages(
            system_prompt=agent.system_prompt,
            user_prompt=agent.user_prompt,
            variables=context,
        )

        llm_response: LLMResponse = await call_llm(
            model=agent.model,
            provider=agent.provider,
            messages=messages,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens,
            api_key=agent.api_key,
            key_id=agent.key_id,
        )

        return AgentTrace(
            agent_name=agent.name,
            model=llm_response.model,
            provider=agent.provider,
            messages_sent=messages,
            output=strip_markdown_fences(llm_response.content),
            tokens_in=llm_response.tokens_in,
            tokens_out=llm_response.tokens_out,
            cost_usd=llm_response.cost_usd,
            latency_ms=llm_response.latency_ms,
        )

    except Exception as e:  # noqa: BLE001 - any agent failure is recorded in the trace
        return AgentTrace(
            agent_name=agent.name,
            model=agent.model,
            provider=agent.provider,
            messages_sent=[],
            output="",
            error=str(e),
        )
