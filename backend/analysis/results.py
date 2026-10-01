"""
Reading results files, whatever version of maestro-bench wrote them.

Current files (2.x) list rows under "rows", each with its agents' outputs
under "agents". Files written before 2.0 list them under "results", with the
agents under "maestro_response.results"; they are converted to the current
shape so the rest of the analysis only knows one format.
"""


def result_rows(data: dict) -> list[dict]:
    """Rows of a results file, in the current (2.x) shape."""
    if "rows" in data:
        return data["rows"] or []
    return [_legacy_row(row) for row in data.get("results") or []]


def row_count(data: dict) -> int:
    """Number of dataset rows an execution processed."""
    total = (data.get("summary") or {}).get("total_rows")
    if isinstance(total, int):
        return total
    return len(result_rows(data))


def _legacy_row(row: dict) -> dict:
    response = row.get("maestro_response") or {}
    agents = [
        {
            "name": agent.get("agent_name"),
            "output": agent.get("result"),
            "error": agent.get("error"),
        }
        for agent in response.get("results") or []
    ]
    errors = response.get("errors") or []
    return {
        "row_index": row.get("row_index"),
        "input_data": row.get("input_data") or {},
        "agents": agents,
        # Rows that failed before reaching the pipeline have no response at all
        "error": row.get("error") or (errors[0] if errors else None),
    }
