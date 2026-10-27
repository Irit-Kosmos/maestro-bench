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
from jinja2.exceptions import SecurityError

from core.prompt_renderer import render_prompt


def test_the_sandbox_renders_like_the_plain_environment():
    template = "{% for x in items %}{{ x | upper }} {% endfor %}{{ name }}"
    variables = {"items": ["a", "b"], "name": "n"}
    assert render_prompt(template, variables, sandboxed=True) == render_prompt(
        template, variables
    )


def test_the_sandbox_refuses_unsafe_attribute_access():
    with pytest.raises(SecurityError):
        render_prompt("{{ x.__class__.__mro__ }}", {"x": 1}, sandboxed=True)
