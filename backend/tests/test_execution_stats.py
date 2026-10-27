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

from execution_stats import latest_figures
from tables import ExperimentExecution


def _execution(status: str) -> ExperimentExecution:
    return ExperimentExecution(experiment_id=1, dataset_snapshot="{}", status=status)


def test_lists_the_status_of_every_execution_newest_first():
    figures = latest_figures([_execution("completed"), _execution("failed"), _execution("cancelled")])

    assert figures["execution_count"] == 3
    assert figures["execution_statuses"] == ["completed", "failed", "cancelled"]


def test_has_no_status_without_execution():
    figures = latest_figures([])

    assert figures["execution_count"] == 0
    assert figures["execution_statuses"] == []
