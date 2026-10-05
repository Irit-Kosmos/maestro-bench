import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from api import aggregators, experiments
from db import get_session
from experiment_utils import (
    build_agent_configs_from_snapshot,
    create_execution_snapshot,
)
from tables import (
    Agent,
    AgentExecutionSnapshot,
    AgentTeam,
    Dataset,
    Experiment,
    ExperimentExecution,
    Model,
    Prompt,
    PromptVersion,
)

FORMULAS = [
    {"name": "score", "formula": "w1 * langue + w2 * contenu"},
    {"name": "admis", "formula": "score >= 3"},
]


@pytest.fixture
def client(engine, monkeypatch):
    # Creating an experiment starts it: not here
    monkeypatch.setattr(experiments.async_jobs, "start_experiment", lambda _id: None)
    app = FastAPI()
    app.include_router(aggregators.router)
    app.include_router(experiments.router)

    def _session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _session
    return TestClient(app)


@pytest.fixture
def setup(engine):
    """A team with two LLM judges and an aggregator, and a dataset."""
    with Session(engine) as s:
        team = AgentTeam(name="Graders")
        dataset = Dataset(name="answers", file_path="answers.csv")
        model = Model(name="gpt", provider="openai")
        prompt = Prompt(name="Judge")
        s.add_all([team, dataset, model, prompt])
        s.flush()
        version = PromptVersion(prompt_id=prompt.id, version="1", user_prompt="{{ a }}")
        s.add(version)
        s.flush()
        langue = Agent(
            name="Langue",
            team_id=team.id,
            default_model_id=model.id,
            default_prompt_version_id=version.id,
        )
        contenu = Agent(
            name="Contenu",
            team_id=team.id,
            default_model_id=model.id,
            default_prompt_version_id=version.id,
        )
        final = Agent(
            name="Final",
            team_id=team.id,
            kind="aggregator",
        )
        s.add_all([langue, contenu, final])
        s.commit()
        return {
            "team": team.id,
            "dataset": dataset.id,
            "langue": langue.id,
            "contenu": contenu.id,
            "final": final.id,
        }


def mappings(ids, contenu_path="score"):
    return [
        {
            "variable": "langue",
            "source": "agent",
            "sourceAgentId": ids["langue"],
            "sourceOutput": "output",
            "sourcePath": "score",
        },
        {
            "variable": "contenu",
            "source": "agent",
            "sourceAgentId": ids["contenu"],
            "sourceOutput": "output",
            "sourcePath": contenu_path,
        },
        {"variable": "w1", "source": "static", "staticValue": "0.4"},
        {"variable": "w2", "source": "static", "staticValue": "0.6"},
    ]


def experiment_body(ids, final_config):
    return {
        "name": "Run",
        "dataset_id": ids["dataset"],
        "agent_teams": [str(ids["team"])],
        "agent_configurations": {
            str(ids["langue"]): {"execution_order": 1},
            str(ids["contenu"]): {"execution_order": 2},
            str(ids["final"]): {"execution_order": 3, "formulas": FORMULAS, **final_config},
        },
    }


# ---------------------------------------------------------------------------
# Experiment creation
# ---------------------------------------------------------------------------


def test_creates_aggregator_config_with_its_formulas(client, engine, setup):
    response = client.post(
        "/experiments",
        json=experiment_body(setup, {"input_mappings": mappings(setup)}),
    )

    assert response.status_code == 201, response.text
    configs = {c["agent_id"]: c for c in response.json()["experiment_configs"]}
    final = configs[setup["final"]]
    assert final["formulas"] == FORMULAS
    assert final["model_id"] is None and final["prompt_version_id"] is None


@pytest.mark.parametrize(
    ("final_config", "message"),
    [
        (lambda ids: {"formulas": [], "input_mappings": mappings(ids)}, "no formula"),
        (lambda ids: {"input_mappings": []}, 'variable "langue" is not mapped'),
        (
            lambda ids: {"input_mappings": mappings({**ids, "contenu": 999})},
            "not in the experiment",
        ),
        (
            lambda ids: {"formulas": [{"name": "score", "formula": "langue +"}]},
            'output "score": syntax error',
        ),
        (
            lambda ids: {"execution_order": 0, "input_mappings": mappings(ids)},
            "does not run before the aggregator",
        ),
    ],
)
def test_refuses_aggregators_that_cannot_run(client, setup, final_config, message):
    response = client.post(
        "/experiments", json=experiment_body(setup, final_config(setup))
    )

    assert response.status_code == 422
    assert response.json()["detail"].startswith('Aggregator "Final"')
    assert message in response.json()["detail"]


def test_snapshot_round_trip(client, engine, setup):
    response = client.post(
        "/experiments",
        json=experiment_body(setup, {"input_mappings": mappings(setup)}),
    )
    experiment_id = response.json()["id"]

    with Session(engine) as s:
        execution = create_execution_snapshot(experiment_id, s)
        snapshot = s.exec(
            select(AgentExecutionSnapshot).where(
                AgentExecutionSnapshot.agent_id == setup["final"]
            )
        ).one()
        assert snapshot.kind == "aggregator"
        assert snapshot.model_name_snapshot == ""
        assert json.loads(snapshot.final_formulas) == FORMULAS

        configs = build_agent_configs_from_snapshot(execution, s)

    final = next(c for c in configs if c.agent_id == setup["final"])
    assert final.kind == "aggregator"
    assert final.formulas == FORMULAS
    assert final.execution_order == 3
    assert len(final.input_mappings) == 4


# ---------------------------------------------------------------------------
# Formula checks, previews and output paths
# ---------------------------------------------------------------------------


def test_check_reports_errors_and_variables(client):
    response = client.post(
        "/aggregators/check",
        json={"formulas": [*FORMULAS, {"name": "bad", "formula": "open(1)"}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["errors"][:2] == [None, None]
    assert "unknown function" in body["errors"][2]
    assert body["variables"] == ["w1", "langue", "w2", "contenu"]


def _add_completed_execution(engine, ids, tmp_path, rows, version=None) -> int:
    (tmp_path / "results").mkdir(exist_ok=True)
    path = tmp_path / "results" / f"results-{version}.json"
    path.write_text(json.dumps({"rows": rows}))
    with Session(engine) as s:
        experiment = Experiment(name="Past run", dataset_id=ids["dataset"])
        s.add(experiment)
        s.flush()
        execution = ExperimentExecution(
            experiment_id=experiment.id,
            dataset_snapshot="{}",
            status="completed",
            results_file_path=str(path.relative_to(tmp_path)),
        )
        s.add(execution)
        s.flush()
        for order, key in enumerate(["langue", "contenu"], start=1):
            s.add(
                AgentExecutionSnapshot(
                    execution_id=execution.id,
                    agent_id=ids[key],
                    agent_name_snapshot=key.capitalize(),
                    model_name_snapshot="gpt",
                    model_provider_snapshot="openai",
                    prompt_name_snapshot="Judge",
                    prompt_version_snapshot="1",
                    prompt_version_id=version,
                    execution_order=order,
                )
            )
        s.commit()
        return execution.id


ROWS = [
    {
        "row_index": 1,
        "input_data": {"answer": "a"},
        "agents": [
            {
                "name": "Langue",
                "output": {"score": 3, "why": "ok", "dist": [0.2, 0.8]},
                "error": None,
            },
            {"name": "Contenu", "output": {"score": 4}, "error": None},
        ],
    },
    {
        "row_index": 2,
        "input_data": {"answer": "b"},
        "agents": [
            {"name": "Langue", "output": {"score": 2}, "error": None},
            {"name": "Contenu", "output": {"note": 1}, "error": None},
        ],
    },
]


def test_preview_evaluates_rows_of_a_past_execution(client, engine, setup, tmp_path):
    execution_id = _add_completed_execution(engine, setup, tmp_path, ROWS)

    response = client.post(
        "/aggregators/preview",
        json={"formulas": FORMULAS, "input_mappings": mappings(setup)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_id"] == execution_id
    assert body["experiment_name"] == "Past run"
    first, second = body["rows"]
    assert first["output"]["score"] == pytest.approx(3.6)
    assert first["inputs"]["langue"] == 3
    assert second["output"] is None
    assert 'path "score" not found in the output of Contenu' in second["error"]


def test_preview_without_a_matching_execution(client, setup):
    response = client.post(
        "/aggregators/preview",
        json={"formulas": FORMULAS, "input_mappings": mappings(setup)},
    )
    assert response.json()["execution_id"] is None
    assert response.json()["rows"] == []


def test_output_paths_of_an_agent(client, engine, setup, tmp_path):
    _add_completed_execution(engine, setup, tmp_path, ROWS)

    response = client.get(f"/agents/{setup['langue']}/output-paths")

    assert response.json() == {
        "agent_id": setup["langue"],
        "paths": ["score", "why"],
        "list_paths": ["dist"],
    }


def test_output_paths_of_one_prompt_version(client, engine, setup, tmp_path):
    old = [
        {
            "row_index": 1,
            "input_data": {},
            "agents": [{"name": "Langue", "output": {"score": [0.1, 0.9]}}],
        }
    ]
    _add_completed_execution(engine, setup, tmp_path, old, version=1)
    _add_completed_execution(engine, setup, tmp_path, ROWS, version=2)

    url = f"/agents/{setup['langue']}/output-paths"
    v1 = client.get(url, params={"prompt_version_id": 1}).json()
    v2 = client.get(url, params={"prompt_version_id": 2}).json()
    v3 = client.get(url, params={"prompt_version_id": 3}).json()

    assert (v1["paths"], v1["list_paths"]) == ([], ["score"])
    assert v2["paths"] == ["score", "why"]
    assert (v3["paths"], v3["list_paths"]) == ([], [])


def test_preview_prefers_the_experiment_prompt_versions(
    client, engine, setup, tmp_path
):
    v1 = _add_completed_execution(engine, setup, tmp_path, ROWS, version=1)
    _add_completed_execution(engine, setup, tmp_path, ROWS, version=2)
    body = {"formulas": FORMULAS, "input_mappings": mappings(setup)}

    matched = client.post(
        "/aggregators/preview",
        json={**body, "prompt_versions": {setup["langue"]: 1, setup["contenu"]: 1}},
    ).json()
    fallback = client.post(
        "/aggregators/preview",
        json={**body, "prompt_versions": {setup["langue"]: 9}},
    ).json()

    assert (matched["execution_id"], matched["versions_match"]) == (v1, True)
    assert fallback["execution_id"] is not None
    assert fallback["versions_match"] is False
