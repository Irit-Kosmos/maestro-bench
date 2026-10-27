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

import pytest

from core.steps import split_step, step_key


@pytest.mark.parametrize(
    ("step", "parsed"), [("12", (12, 1)), ("12#2", (12, 2)), (12, (12, 1))]
)
def test_a_step_key_reads_as_its_agent_and_instance(step, parsed):
    assert split_step(step) == parsed
    assert step_key(*parsed) == str(step)


@pytest.mark.parametrize(
    "step", ["abc", "12#x", "012", " 12", "12#1", "12#", "12#0", "12#-3"]
)
def test_only_the_written_form_is_a_step_key(step):
    with pytest.raises(ValueError, match="Invalid step"):
        split_step(step)
