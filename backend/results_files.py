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
from tables import ExperimentExecution

logger = logging.getLogger(__name__)


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
    if not execution.results_file_path:
        return None
    path = Path(execution.results_file_path)
    try:
        stat = path.stat()
    except OSError:
        return None
    return _row_count(str(path), stat.st_mtime_ns, stat.st_size)
