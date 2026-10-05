"""
Facts read from execution results files, cached while the file is unchanged.

A completed execution's results file never changes, so lists that show a row
count for every execution only parse each file once.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

from analysis import row_count
from config import DATA_DIR
from tables import ExperimentExecution

logger = logging.getLogger(__name__)


def get_data_dir() -> Path:
    return DATA_DIR.resolve()


def get_results_dir() -> Path:
    return get_data_dir() / "results"


def results_path(execution: ExperimentExecution) -> Path | None:
    """
    Absolute path of an execution's results file, or None when it has none.

    The stored path is relative to the data directory. Anything that resolves
    outside the results directory is refused.
    """
    if not execution.results_file_path:
        return None
    path = (get_data_dir() / execution.results_file_path).resolve()
    if get_results_dir() not in path.parents:
        logger.warning(
            "Ignoring results path outside the results directory: %s",
            execution.results_file_path,
        )
        return None
    return path


@lru_cache(maxsize=512)
def _row_count(path: str, mtime_ns: int, size: int) -> int | None:
    try:
        with open(path) as f:
            return row_count(json.load(f))
    except (OSError, ValueError) as e:
        logger.warning("Could not read results file %s: %s", path, e)
        return None


def execution_row_count(execution: ExperimentExecution) -> int | None:
    """Rows processed by an execution, or None while it has no results file."""
    path = results_path(execution)
    if path is None:
        return None
    try:
        stat = path.stat()
    except OSError:
        return None
    return _row_count(str(path), stat.st_mtime_ns, stat.st_size)
