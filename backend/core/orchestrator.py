"""
Sequential agent pipeline orchestrator.

Executes a list of agents in order, passing each agent's output
as context to subsequent agents. Collects per-agent traces
(prompts, responses, token usage, latency, cost).
"""

from dataclasses import dataclass, field

from core.llm import LLMResponse, call_llm
from core.prompt_renderer import build_messages


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


@dataclass
class PipelineResult:
    """Result of running the full agent pipeline on one data row."""

    row_index: int
    input_data: dict  # Dataset row (column name -> value)
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
            "input_data": {k: _safe_serialize(v) for k, v in self.input_data.items()},
            "agents": [
                {
                    "name": t.agent_name,
                    "model": t.model,
                    "provider": t.provider,
                    "messages_sent": t.messages_sent,
                    "output": _try_parse_json(t.output),
                    "tokens_in": t.tokens_in,
                    "tokens_out": t.tokens_out,
                    "cost_usd": t.cost_usd,
                    "latency_ms": round(t.latency_ms, 1),
                    "error": t.error,
                }
                for t in self.agent_traces
            ],
            "final_output": _try_parse_json(self.final_output),
            "totals": {
                "tokens_in": self.total_tokens_in,
                "tokens_out": self.total_tokens_out,
                "cost_usd": self.total_cost_usd,
                "latency_ms": round(self.total_latency_ms, 1),
            },
            "error": self.error,
        }


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) wrapping LLM output."""
    import re

    stripped = text.strip()
    m = re.match(r"^```(?:\w*)\n(.*?)```$", stripped, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text


def _try_parse_json(text: str):
    """Try to parse text as JSON; return parsed object or original string."""
    import json

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def _safe_serialize(value):
    """Convert pandas/numpy types to JSON-safe Python types."""
    import math

    if hasattr(value, "item"):  # numpy scalar
        return value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _resolve_agent_context(
    agent: AgentConfig,
    shared_context: dict,
    row: dict,
    agent_outputs: dict,
) -> dict:
    """
    Build the variable context for a single agent.

    If the agent has explicit input_mappings, use them to map dataset columns,
    previous agent outputs, or static values to prompt variables.
    Otherwise fall back to the full shared context (dataset row + all previous
    agent outputs).
    """
    if not agent.input_mappings:
        return shared_context

    resolved: dict = {}
    for mapping in agent.input_mappings:
        variable = mapping.get("variable")
        source = mapping.get("source")
        if not variable or not source:
            continue

        if source == "dataset":
            column = mapping.get("sourceColumn")
            resolved[variable] = row.get(column) if column else None
        elif source == "agent":
            source_agent_id = mapping.get("sourceAgentId")
            output_field = mapping.get("sourceOutput", "output")
            key = f"agent_{source_agent_id}_{output_field}"
            resolved[variable] = agent_outputs.get(key)
        elif source == "static":
            resolved[variable] = mapping.get("staticValue")

    return resolved


async def run_pipeline(
    agents: list[AgentConfig],
    row: dict,
    row_index: int = 0,
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
        row_index: Index of this row in the dataset

    Returns:
        PipelineResult with all agent traces and aggregated metrics
    """
    result = PipelineResult(row_index=row_index, input_data=row)

    # Shared context: starts with the row, accumulates agent outputs
    context = dict(row)

    # Keep track of agent outputs by agent id for explicit mappings
    agent_outputs: dict = {}

    # Sort agents by execution_order
    sorted_agents = sorted(agents, key=lambda a: a.execution_order)

    for agent in sorted_agents:
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
            agent_outputs[f"agent_{agent.agent_id}_output"] = trace.output

    # Final output = last successful agent's output
    if result.agent_traces:
        last_trace = result.agent_traces[-1]
        result.final_output = last_trace.output if not last_trace.error else ""

    return result


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
        )

        return AgentTrace(
            agent_name=agent.name,
            model=llm_response.model,
            provider=agent.provider,
            messages_sent=messages,
            output=_strip_markdown_fences(llm_response.content),
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
