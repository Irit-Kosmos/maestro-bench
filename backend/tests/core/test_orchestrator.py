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

import asyncio
import json

import pytest

from core import orchestrator
from core.llm import LLMResponse
from core.orchestrator import AgentConfig, run_pipeline


@pytest.fixture
def llm(monkeypatch):
    """Answer each agent with the canned output of its model, recording prompts."""
    answers: dict[str, str] = {}
    prompts: list[str] = []

    async def fake_call_llm(model, provider, messages, temperature, max_tokens, **_):
        prompts.append(messages[-1]["content"] if messages else "")
        return LLMResponse(content=answers[model], tokens_in=10, cost_usd=0.01)

    monkeypatch.setattr(orchestrator, "call_llm", fake_call_llm)
    return answers, prompts


def judge(agent_id: int, name: str, order: int, **fields) -> AgentConfig:
    return AgentConfig(
        name=name,
        system_prompt=None,
        user_prompt=fields.pop("user_prompt", "Grade {{ answer }}"),
        variables=[],
        model=name,
        provider="fake",
        execution_order=order,
        agent_id=agent_id,
        **fields,
    )


def aggregator(agent_id: int, order: int, formulas, mappings) -> AgentConfig:
    return AgentConfig(
        name="Final",
        system_prompt=None,
        user_prompt=None,
        variables=[],
        model="",
        provider="",
        execution_order=order,
        agent_id=agent_id,
        kind="aggregator",
        formulas=formulas,
        input_mappings=mappings,
    )


def from_agent(variable, agent_id, path=""):
    return {
        "variable": variable,
        "source": "agent",
        "sourceAgentId": agent_id,
        "sourceOutput": "output",
        "sourcePath": path,
    }


def static(variable, value):
    return {"variable": variable, "source": "static", "staticValue": value}


WEIGHTED = [
    {"name": "score", "formula": "w1 * langue + w2 * contenu"},
    {"name": "admis", "formula": "score >= 3"},
]
WEIGHTED_MAPPINGS = [
    from_agent("langue", 1, "score"),
    from_agent("contenu", 2, "eval.score"),
    static("w1", "0.4"),
    static("w2", "0.6"),
]


def run(agents, row=None):
    return asyncio.run(run_pipeline(agents, row or {"answer": "42"}, row_index=1))


def test_aggregator_combines_previous_outputs(llm):
    answers, _ = llm
    answers["Langue"] = '{"score": 3}'
    answers["Contenu"] = '```json\n{"eval": {"score": "4"}}\n```'

    result = run(
        [
            judge(1, "Langue", 1),
            judge(2, "Contenu", 2),
            aggregator(3, 3, WEIGHTED, WEIGHTED_MAPPINGS),
        ]
    ).to_dict()

    final = result["agents"][2]
    assert final["kind"] == "aggregator"
    assert final["error"] is None
    assert final["inputs"] == {"langue": 3, "contenu": 4, "w1": 0.4, "w2": 0.6}
    assert final["output"]["score"] == pytest.approx(3.6)
    assert final["output"]["admis"] is True
    assert final["tokens_in"] == 0 and final["cost_usd"] == 0
    assert result["final_output"] == final["output"]
    assert result["error"] is None
    # Only the LLM agents count in the totals
    assert result["totals"]["tokens_in"] == 20


def test_aggregator_reads_dataset_columns_and_whole_outputs(llm):
    answers, _ = llm
    answers["Langue"] = "4"

    result = run(
        [
            judge(1, "Langue", 1),
            aggregator(
                2,
                2,
                [{"name": "ecart", "formula": "abs(langue - attendu)"}],
                [
                    from_agent("langue", 1),
                    {"variable": "attendu", "source": "dataset", "sourceColumn": "gt"},
                ],
            ),
        ],
        row={"answer": "x", "gt": 2},
    ).to_dict()

    assert result["agents"][1]["output"] == {"ecart": 2}


@pytest.mark.parametrize(
    ("contenu_output", "message"),
    [
        (
            '{"note": 4}',
            'variable "contenu": path "eval.score" not found in the output of Contenu',
        ),
        ('{"eval": {"score": "4/5"}}', "expected a number"),
        ('{"eval": {"score": null}}', 'variable "contenu" has no value'),
        ('{"eval": {"score": [4]}}', "expected a number, got a list"),
        ('{"eval": {"score": {"a": 4}}}', 'variable "contenu" is an object'),
    ],
)
def test_aggregator_is_strict_about_its_inputs(llm, contenu_output, message):
    answers, _ = llm
    answers["Langue"] = '{"score": 3}'
    answers["Contenu"] = contenu_output

    result = run(
        [
            judge(1, "Langue", 1),
            judge(2, "Contenu", 2),
            aggregator(3, 3, WEIGHTED, WEIGHTED_MAPPINGS),
        ]
    ).to_dict()

    final = result["agents"][2]
    assert message in final["error"]
    assert final["output"] == ""
    assert result["error"].startswith("Agent 'Final' failed")


def test_unmapped_variable_is_an_error(llm):
    answers, _ = llm
    answers["Langue"] = '{"score": 3}'

    result = run(
        [
            judge(1, "Langue", 1),
            aggregator(
                2,
                2,
                [{"name": "score", "formula": "langue * w"}],
                [from_agent("langue", 1, "score")],
            ),
        ]
    ).to_dict()

    assert result["agents"][1]["error"] == 'variable "w" is not mapped'


def test_llm_agents_read_a_path_of_an_earlier_output(llm):
    answers, prompts = llm
    answers["Langue"] = '{"score": 3, "details": {"a": 1}}'
    answers["Relecture"] = "ok"

    run(
        [
            judge(1, "Langue", 1),
            judge(
                2,
                "Relecture",
                2,
                user_prompt="{{ note }} / {{ details }} / {{ brut }}",
                input_mappings=[
                    from_agent("note", 1, "score"),
                    from_agent("details", 1, "details"),
                    {
                        "variable": "brut",
                        "source": "agent",
                        "sourceAgentId": 1,
                        "sourceOutput": "output",
                    },
                ],
            ),
        ]
    )

    assert prompts[1] == '3 / {"a": 1} / {"score": 3, "details": {"a": 1}}'


def test_llm_agents_can_read_an_aggregator(llm):
    answers, prompts = llm
    answers["Langue"] = '{"score": 3}'
    answers["Avis"] = "ok"

    run(
        [
            judge(1, "Langue", 1),
            aggregator(
                2,
                2,
                [{"name": "double", "formula": "2 * langue"}],
                [from_agent("langue", 1, "score")],
            ),
            judge(
                3,
                "Avis",
                3,
                user_prompt="{{ final }}",
                input_mappings=[from_agent("final", 2, "double")],
            ),
        ]
    )

    assert prompts[1] == "6"


def test_results_keep_aggregator_output_as_json():
    # The raw output stays a string so {{ Final_output }} renders as JSON
    trace = orchestrator.run_aggregator(
        aggregator(1, 1, [{"name": "s", "formula": "1 + 1"}], []), {}, {}, {}
    )
    assert json.loads(trace.output) == {"s": 2}


def test_an_agent_can_run_twice_and_each_step_is_read_on_its_own(llm):
    answers, prompts = llm
    answers["Langue"] = '{"score": 3}'
    answers["Langue #2"] = '{"score": 5}'
    answers["Avis"] = "ok"

    result = run(
        [
            judge(1, "Langue", 1),
            judge(1, "Langue #2", 2, step_key="1#2"),
            judge(
                2,
                "Avis",
                3,
                user_prompt="{{ first }} / {{ second }} / {{ Langue_2_output }}",
                input_mappings=[
                    {"variable": "first", "source": "agent", "sourceStep": "1",
                     "sourcePath": "score"},
                    {"variable": "second", "source": "agent", "sourceStep": "1#2",
                     "sourcePath": "score"},
                ],
            ),
        ]
    ).to_dict()

    assert prompts[2].startswith("3 / 5 / ")
    assert [a["step_key"] for a in result["agents"]] == ["1", "1#2", "2"]


def test_an_aggregator_reads_the_step_it_is_mapped_to(llm):
    answers, _ = llm
    answers["Langue"] = '{"score": 3}'
    answers["Langue #2"] = '{"score": 5}'

    result = run(
        [
            judge(1, "Langue", 1),
            judge(1, "Langue #2", 2, step_key="1#2"),
            aggregator(
                2,
                3,
                [{"name": "gap", "formula": "second - first"}],
                [
                    {"variable": "first", "source": "agent", "sourceStep": "1",
                     "sourcePath": "score"},
                    {"variable": "second", "source": "agent", "sourceStep": "1#2",
                     "sourcePath": "score"},
                ],
            ),
        ]
    ).to_dict()

    assert result["agents"][2]["output"] == {"gap": 2}
