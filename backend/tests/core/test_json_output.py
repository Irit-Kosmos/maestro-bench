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

from core.json_output import parse_json_output, strip_markdown_fences


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"score": 4}', {"score": 4}),
        ('```json\n{"score": 4}\n```', {"score": 4}),
        (
            '{\n  "score": 0,\n  "reasoning": "short",\n}',
            {"score": 0, "reasoning": "short"},
        ),
        ('{"labels": ["a", "b",]}', {"labels": ["a", "b"]}),
        ("4", 4),
    ],
)
def test_parses_json_outputs(text, expected):
    assert parse_json_output(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Please provide the learner's answer.",
        '{"reasoning": "invalid escape \\0 here"}',
        "",
    ],
)
def test_leaves_non_json_as_text(text):
    assert parse_json_output(text) == text


def test_valid_json_is_not_rewritten():
    # A ", }" inside a string must survive: repair only runs on invalid JSON
    assert parse_json_output('{"note": "a, }"}') == {"note": "a, }"}


def test_non_string_passthrough():
    assert parse_json_output({"score": 1}) == {"score": 1}
    assert parse_json_output(None) is None


def test_strip_markdown_fences():
    assert strip_markdown_fences("```\nabc\n```") == "abc"
    assert strip_markdown_fences("no fences") == "no fences"
