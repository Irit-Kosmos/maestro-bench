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

import config
import credentials
from experiment_utils import build_agent_configs_from_snapshot
from tables import AgentExecutionSnapshot, Dataset, Experiment, ExperimentExecution


@pytest.fixture
def execution(session):
    dataset = Dataset(name="d", file_path="d.csv")
    session.add(dataset)
    session.flush()
    experiment = Experiment(name="e", dataset_id=dataset.id)
    session.add(experiment)
    session.flush()
    execution = ExperimentExecution(experiment_id=experiment.id, dataset_snapshot="{}")
    session.add(execution)
    session.flush()
    for order, provider in enumerate(("mistral", "openai", "mistral")):
        session.add(
            AgentExecutionSnapshot(
                execution_id=execution.id,
                agent_id=None,
                agent_name_snapshot=f"agent {order}",
                model_name_snapshot="m",
                model_provider_snapshot=provider,
                prompt_name_snapshot="p",
                prompt_version_snapshot="1",
                execution_order=order,
            )
        )
    session.commit()
    return execution


def test_agents_call_their_provider_with_the_workspace_key(
    session, execution, monkeypatch
):
    monkeypatch.setattr(config, "ENCRYPTION_KEY", "e" * 40)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    credentials.set_key(session, "mistral", "sk-workspace-1234")

    agents = build_agent_configs_from_snapshot(execution, session)

    assert [(a.provider, a.api_key) for a in agents] == [
        ("mistral", "sk-workspace-1234"),
        ("openai", None),
        ("mistral", "sk-workspace-1234"),
    ]
    assert agents[0].key_id == agents[2].key_id != agents[1].key_id
    assert "sk-workspace-1234" not in repr(agents[0])
