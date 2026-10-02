"""What the lists of experiments and batches say about an experiment's executions."""

from collections.abc import Sequence

from tables import ExperimentExecution


def duration_seconds(execution: ExperimentExecution) -> float | None:
    """How long an execution took, or None while it is still running."""
    if execution.completed_at is None:
        return None
    return (execution.completed_at - execution.started_at).total_seconds()


def latest_figures(executions: Sequence[ExperimentExecution]) -> dict:
    """Execution count of an experiment, and the figures of its latest execution.

    The latest one is the one the experiment currently stands for; earlier ones
    are only counted, and their statuses listed. `executions` are ordered from the
    newest to the oldest.
    """
    latest = executions[0] if executions else None
    return {
        "execution_count": len(executions),
        "execution_statuses": [execution.status for execution in executions],
        "duration_seconds": duration_seconds(latest) if latest else None,
        "rows_failed": latest.rows_failed if latest else None,
        "total_tokens": latest.total_tokens if latest else None,
        "total_cost_usd": latest.total_cost_usd if latest else None,
    }
