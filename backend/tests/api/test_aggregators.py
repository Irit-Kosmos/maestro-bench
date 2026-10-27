import json

import pytest
from sqlmodel import select

from api import aggregators, experiments
from experiment_utils import (
    build_agent_configs_from_snapshot,
    create_execution_snapshot,
)
from tables import (
    Agent,
    AgentExecutionSnapshot,
    Dataset,
    Experiment,
    ExperimentExecution,
    Model,
    Prompt,
    PromptVersion,
)
from tests.conftest import api_client, scoped

FORMULAS = [
    {"name": "score", "formula": "w1 * langue + w2 * contenu"},
    {"name": "admis", "formula": "score >= 3"},
]


@pytest.fixture
def client(engine, monkeypatch):
    # Creating an experiment starts it: not here
    monkeypatch.setattr(experiments.async_jobs, "start_experiment", lambda *_: "started")
    return api_client(engine, aggregators, experiments)


@pytest.fixture
def setup(engine):
    """Two LLM judges and an aggregator, and a dataset."""
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        model = Model(name="gpt", provider="openai")
        prompt = Prompt(name="Judge")
        s.add_all([dataset, model, prompt])
        s.flush()
        version = PromptVersion(prompt_id=prompt.id, version="1", user_prompt="{{ a }}")
        s.add(version)
        s.flush()
        langue = Agent(
            name="Langue",
            default_model_id=model.id,
            default_prompt_version_id=version.id,
        )
        contenu = Agent(
            name="Contenu",
            default_model_id=model.id,
            default_prompt_version_id=version.id,
        )
        final = Agent(
            name="Final",
            kind="aggregator",
        )
        s.add_all([langue, contenu, final])
        s.commit()
        return {
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

    with scoped(engine) as s:
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


def _add_completed_execution(engine, ids, results_dir, rows, version=None) -> int:
    path = results_dir / f"results-{version}.json"
    path.write_text(json.dumps({"rows": rows}))
    with scoped(engine) as s:
        experiment = Experiment(name="Past run", dataset_id=ids["dataset"])
        s.add(experiment)
        s.flush()
        execution = ExperimentExecution(
            experiment_id=experiment.id,
            dataset_snapshot="{}",
            status="completed",
            results_file_path=path.name,
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


def test_preview_evaluates_rows_of_a_past_execution(client, engine, setup, results_dir):
    execution_id = _add_completed_execution(engine, setup, results_dir, ROWS)

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


def test_output_paths_of_an_agent(client, engine, setup, results_dir):
    _add_completed_execution(engine, setup, results_dir, ROWS)

    response = client.get(f"/agents/{setup['langue']}/output-paths")

    assert response.json() == {
        "agent_id": setup["langue"],
        "paths": ["score", "why"],
        "list_paths": ["dist"],
    }


def test_output_paths_of_one_prompt_version(client, engine, setup, results_dir):
    old = [
        {
            "row_index": 1,
            "input_data": {},
            "agents": [{"name": "Langue", "output": {"score": [0.1, 0.9]}}],
        }
    ]
    _add_completed_execution(engine, setup, results_dir, old, version=1)
    _add_completed_execution(engine, setup, results_dir, ROWS, version=2)

    url = f"/agents/{setup['langue']}/output-paths"
    v1 = client.get(url, params={"prompt_version_id": 1}).json()
    v2 = client.get(url, params={"prompt_version_id": 2}).json()
    v3 = client.get(url, params={"prompt_version_id": 3}).json()

    assert (v1["paths"], v1["list_paths"]) == ([], ["score"])
    assert v2["paths"] == ["score", "why"]
    assert (v3["paths"], v3["list_paths"]) == ([], [])


def test_output_paths_of_a_version_another_step_of_the_agent_ran(
    client, engine, setup, results_dir
):
    """The agent ran twice, the second time with the version asked."""
    path = results_dir / "results-twice.json"
    rows = [
        {
            "row_index": 1,
            "input_data": {},
            "agents": [
                {"name": "Langue", "output": {"old": 1}},
                {"name": "Langue #2", "output": {"score": 3}},
            ],
        }
    ]
    path.write_text(json.dumps({"rows": rows}))
    with scoped(engine) as s:
        experiment = Experiment(name="Twice", dataset_id=setup["dataset"])
        s.add(experiment)
        s.flush()
        execution = ExperimentExecution(
            experiment_id=experiment.id,
            dataset_snapshot="{}",
            status="completed",
            results_file_path=path.name,
        )
        s.add(execution)
        s.flush()
        for order, (key, name, version) in enumerate(
            [("", "Langue", 1), ("#2", "Langue #2", 2)], start=1
        ):
            s.add(
                AgentExecutionSnapshot(
                    execution_id=execution.id,
                    agent_id=setup["langue"],
                    step_key=f"{setup['langue']}{key}",
                    agent_name_snapshot=name,
                    model_name_snapshot="gpt",
                    model_provider_snapshot="openai",
                    prompt_name_snapshot="Judge",
                    prompt_version_snapshot=str(version),
                    prompt_version_id=version,
                    execution_order=order,
                )
            )
        s.commit()

    response = client.get(
        f"/agents/{setup['langue']}/output-paths", params={"prompt_version_id": 2}
    )

    assert response.json()["paths"] == ["score"]


def test_preview_prefers_the_experiment_prompt_versions(
    client, engine, setup, results_dir
):
    v1 = _add_completed_execution(engine, setup, results_dir, ROWS, version=1)
    _add_completed_execution(engine, setup, results_dir, ROWS, version=2)
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


# ---------------------------------------------------------------------------
# An agent that runs more than once
# ---------------------------------------------------------------------------


def test_an_agent_can_be_a_step_of_the_experiment_twice(client, engine, setup):
    body = experiment_body(setup, {"input_mappings": []})
    body["agent_configurations"][f"{setup['langue']}#2"] = {"execution_order": 2}
    body["agent_configurations"][str(setup["final"])] = {
        "execution_order": 3,
        "formulas": [{"name": "gap", "formula": "second - first"}],
        "input_mappings": [
            {"variable": "first", "source": "agent",
             "sourceStep": str(setup["langue"]), "sourcePath": "score"},
            {"variable": "second", "source": "agent",
             "sourceStep": f"{setup['langue']}#2", "sourcePath": "score"},
        ],
    }

    response = client.post("/experiments", json=body)

    assert response.status_code == 201, response.text
    steps = {c["step_key"]: c for c in response.json()["experiment_configs"]}
    assert set(steps) == {
        str(setup["langue"]),
        f"{setup['langue']}#2",
        str(setup["contenu"]),
        str(setup["final"]),
    }
    assert steps[str(setup["langue"])]["label"] is None
    assert steps[f"{setup['langue']}#2"]["label"] == "Langue #2"
    assert steps[f"{setup['langue']}#2"]["agent_id"] == setup["langue"]

    with scoped(engine) as s:
        execution = create_execution_snapshot(response.json()["id"], s)
        agents = build_agent_configs_from_snapshot(execution, s)
    assert [(a.name, a.step_key) for a in agents] == [
        ("Langue", str(setup["langue"])),
        ("Langue #2", f"{setup['langue']}#2"),
        ("Contenu", str(setup["contenu"])),
        ("Final", str(setup["final"])),
    ]


def test_an_aggregator_cannot_read_a_step_that_is_not_there(client, setup):
    body = experiment_body(setup, {})
    body["agent_configurations"][str(setup["final"])]["input_mappings"] = [
        {"variable": "langue", "source": "agent",
         "sourceStep": f"{setup['langue']}#2", "sourcePath": "score"},
        {"variable": "contenu", "source": "agent",
         "sourceStep": str(setup["contenu"]), "sourcePath": "score"},
        {"variable": "w1", "source": "static", "staticValue": "1"},
        {"variable": "w2", "source": "static", "staticValue": "1"},
    ]

    response = client.post("/experiments", json=body)

    assert response.status_code == 422
    assert "not in the experiment" in response.json()["detail"]


def test_a_step_key_must_name_an_agent(client, setup):
    body = experiment_body(setup, {})
    body["agent_configurations"]["abc#2"] = {}

    response = client.post("/experiments", json=body)

    assert response.status_code == 422
    assert "Invalid step" in response.json()["detail"]
