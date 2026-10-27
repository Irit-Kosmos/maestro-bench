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

from analysis import result_rows, row_count
from analysis.extract import ExclusionReason, extract_pairs

LEGACY = {
    "results": [
        {
            "row_index": 1,
            "input_data": {"score_avg": 3.5},
            "maestro_response": {
                "results": [
                    {
                        "agent_name": "Corrector",
                        "result": {"score": 4, "reasoning": "ok"},
                        "error": None,
                    }
                ],
                "success": True,
                "errors": [],
            },
        },
        {
            "row_index": 2,
            "input_data": {"score_avg": 2},
            "maestro_response": {
                "results": [
                    {
                        "agent_name": "Corrector",
                        "result": {},
                        "error": "Error code: 400",
                    }
                ],
                "success": False,
                "errors": ["Corrector.Corrector: Error code: 400"],
            },
        },
        # Failed before reaching the pipeline: no maestro_response
        {
            "row_index": 3,
            "input_data": {"score_avg": 4},
            "error": "MAESTRO API error: Server disconnected",
        },
    ]
}


def test_current_rows_are_returned_as_is():
    rows = [{"row_index": 1, "input_data": {}, "agents": []}]
    assert result_rows({"rows": rows}) == rows


def test_legacy_rows_are_converted():
    rows = result_rows(LEGACY)

    assert rows[0] == {
        "row_index": 1,
        "input_data": {"score_avg": 3.5},
        "agents": [
            {
                "name": "Corrector",
                "output": {"score": 4, "reasoning": "ok"},
                "error": None,
            }
        ],
        "error": None,
    }
    assert rows[1]["agents"][0]["error"] == "Error code: 400"
    assert rows[1]["error"] == "Corrector.Corrector: Error code: 400"
    assert rows[2]["agents"] == []
    assert rows[2]["error"] == "MAESTRO API error: Server disconnected"


def test_legacy_rows_feed_the_extraction():
    extraction = extract_pairs(
        result_rows(LEGACY), "Corrector", "score", "score_avg", "numeric"
    )

    assert extraction.predictions == [4.0]
    assert extraction.truths == [3.5]
    assert [e.reason for e in extraction.excluded] == [
        ExclusionReason.AGENT_ERROR,
        ExclusionReason.AGENT_ERROR,
    ]


def test_empty_file():
    assert result_rows({}) == []


def test_row_count_reads_the_summary():
    assert row_count({"summary": {"total_rows": 3}, "rows": []}) == 3


def test_row_count_falls_back_to_the_rows():
    assert row_count(LEGACY) == 3
    assert row_count({}) == 0
