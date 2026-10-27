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
Evaluation of execution results against a ground-truth column.

Pure computation: no web framework or database dependency, so it can be used
from the API, a script or a notebook.
"""

from analysis.agreement import AgreementResult, compute_agreement
from analysis.compute import (
    AnalysisConfig,
    AnalysisResult,
    RunInput,
    RunResult,
    compute_analysis,
    validate_config,
)
from analysis.metrics import METRICS, Metric
from analysis.results import result_rows, row_count

__all__ = [
    "METRICS",
    "AgreementResult",
    "AnalysisConfig",
    "AnalysisResult",
    "Metric",
    "RunInput",
    "RunResult",
    "compute_agreement",
    "compute_analysis",
    "result_rows",
    "row_count",
    "validate_config",
]
