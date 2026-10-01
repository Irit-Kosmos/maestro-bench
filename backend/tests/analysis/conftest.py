"""Builders for synthetic result rows, shaped like a results file's "rows"."""

import pytest


def make_row(
    row_index: int,
    truth=None,
    output=None,
    agent: str = "Grader",
    error: str | None = None,
    truth_column: str = "score",
    dataset_row_id: int | None = None,
) -> dict:
    agents = (
        []
        if output is _NOT_REACHED
        else [{"name": agent, "output": output, "error": error}]
    )
    row = {
        "row_index": row_index,
        "input_data": {truth_column: truth},
        "agents": agents,
    }
    if dataset_row_id is not None:
        row["dataset_row_id"] = dataset_row_id
    return row


_NOT_REACHED = object()


@pytest.fixture
def not_reached():
    """Pass as `output` for an agent the pipeline never got to."""
    return _NOT_REACHED


def scored_rows(pairs: list[tuple], agent: str = "Grader") -> list[dict]:
    """Rows whose agent output is {"score": pred}, from (pred, truth) pairs."""
    return [
        make_row(i + 1, truth=truth, output={"score": pred}, agent=agent)
        for i, (pred, truth) in enumerate(pairs)
    ]
