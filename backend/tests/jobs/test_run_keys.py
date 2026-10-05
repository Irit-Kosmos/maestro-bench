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
