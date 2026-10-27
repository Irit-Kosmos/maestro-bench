# MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
# Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
# Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

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
from workspace_files import confine, results_dir

logger = logging.getLogger(__name__)


def results_path(execution: ExperimentExecution) -> Path | None:
    """
    Absolute path of an execution's results file, or None when it has none.

    The stored path is relative to the results folder of the execution's own
    workspace. Anything that resolves outside that folder is refused.
    """
    if not execution.results_file_path:
        return None
    try:
        return confine(results_dir(execution.workspace_id), execution.results_file_path)
    except ValueError:
        logger.warning(
            "Ignoring results path outside the results folder: %s",
            execution.results_file_path,
        )
        return None


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
