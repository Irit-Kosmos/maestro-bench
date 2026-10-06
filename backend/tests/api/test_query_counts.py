"""The lists run a fixed number of queries, whatever the amount of data they list.

Each endpoint is called on a small workspace and on a bigger one: reading more
rows must not cost more queries (one per row is the classic N+1).
"""

import json
import uuid
from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session

from api import (
    agent_teams,
    agents,
    aggregators,
    analyses,
    batches,
    dashboard,
    experiment_executions,
    experiments,
    prompts,
    studies,
)
from auth.workspaces import WorkspaceContext, workspace_context
from batch_utils import serialize_point
from db import get_session
from tables import (
    Agent,
    AgentExecutionSnapshot,
    AgentTeam,
    Analysis,
    Batch,
    Dataset,
    Experiment,
    ExperimentAgentConfig,
    ExperimentExecution,
    Model,
    Note,
    Prompt,
    PromptVersion,
    Study,
    StudyItem,
    Tag,
    TagLink,
)
from tests.conftest import TEST_WORKSPACE_ID, scoped
from workspace_scope import scope_session


@pytest.fixture
def client(engine):
    app = FastAPI()
    for module in (
        agent_teams,
        agents,
        aggregators,
        analyses,
        batches,
        dashboard,
        experiment_executions,
        experiments,
        prompts,
        studies,
    ):
        app.include_router(module.router)

    def _session():
        with Session(engine) as session:
            scope_session(session, TEST_WORKSPACE_ID)
            yield session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[workspace_context] = lambda: WorkspaceContext(
        id=TEST_WORKSPACE_ID,
        slug="test",
        name="Test",
        role="owner",
        archived=False,
        user_id=0,
    )
    return TestClient(app)


@contextmanager
def counting(engine):
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


def populate(engine, experiments: int, agents: int, batch_size: int = 2) -> dict:
    """`experiments` experiments with two executions each, grouped in batches.

    Every execution ran `agents` agents. Returns the ids of the first experiment,
    of its first execution, and of the first batch.
    """
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        team = AgentTeam(name="Graders")
        prompt = Prompt(name="Grader")
        s.add_all([dataset, team, prompt])
        s.flush()
        version = PromptVersion(prompt_id=prompt.id, version="1")
        models = [Model(name=n, provider="openai") for n in ("m-a", "m-b")]
        tag = Tag(name=f"tag {uuid.uuid4().hex}")
        s.add_all([version, *models, tag])
        s.flush()
        team_agents = [
            Agent(
                name=f"Agent {i}",
                team_id=team.id,
                default_model_id=models[0].id,
                default_prompt_version_id=version.id,
            )
            for i in range(agents)
        ]
        s.add_all(team_agents)
        s.flush()
        s.add_all(
            [
                TagLink(tag_id=tag.id, kind="agent", item_id=a.id)
                for a in team_agents
            ]
            + [TagLink(tag_id=tag.id, kind="prompt", item_id=prompt.id)]
        )

        first: dict = {"agent": team_agents[0].id, "executions": []}
        batch = None
        made_batches: list[Batch] = []
        made_experiments: list[Experiment] = []
        for i in range(experiments):
            if i % batch_size == 0:
                batch = Batch(
                    name=f"Batch {i}",
                    variations=json.dumps(
                        [
                            {
                                "agent_id": team_agents[0].id,
                                "field": "model_id",
                                "values": [m.id for m in models],
                            }
                        ]
                    ),
                )
                s.add(batch)
                s.flush()
                made_batches.append(batch)
                first.setdefault("batch", batch.id)
            experiment = Experiment(
                name=f"Experiment {i}",
                dataset_id=dataset.id,
                batch_id=batch.id,
                variant=serialize_point(
                    {team_agents[0].id: {"model_id": models[i % 2].id}}
                ),
                status="completed",
            )
            s.add(experiment)
            s.flush()
            made_experiments.append(experiment)
            first.setdefault("experiment", experiment.id)
            s.add_all(
                [
                    ExperimentAgentConfig(
                        experiment_id=experiment.id,
                        agent_id=a.id,
                        model_id=models[0].id,
                        prompt_version_id=version.id,
                        execution_order=n,
                    )
                    for n, a in enumerate(team_agents, start=1)
                ]
            )
            for _ in range(2):
                execution = ExperimentExecution(
                    experiment_id=experiment.id,
                    status="completed",
                    dataset_snapshot=json.dumps({"name": "answers"}),
                    results_file_path="results.json",
                )
                s.add(execution)
                s.flush()
                first.setdefault("execution", execution.id)
                first["executions"].append(execution.id)
                s.add_all(
                    [
                        AgentExecutionSnapshot(
                            execution_id=execution.id,
                            agent_id=a.id,
                            agent_name_snapshot=a.name,
                            model_name_snapshot="m-a",
                            model_provider_snapshot="openai",
                            prompt_name_snapshot="Grader",
                            prompt_version_snapshot="1",
                            prompt_id=prompt.id,
                            prompt_version_id=version.id,
                            execution_order=n,
                        )
                        for n, a in enumerate(team_agents, start=1)
                    ]
                )
        analysis = Analysis(
            name="Analysis",
            config=json.dumps(
                {
                    "truth_column": "truth",
                    "value_type": "numeric",
                    "metrics": ["mae"],
                }
            ),
            runs=json.dumps([]),
        )
        s.add(analysis)
        s.flush()

        # A study for each batch: the batch, its first experiment and the analysis
        for n, made in enumerate(made_batches):
            study = Study(name=f"Study {n}")
            s.add(study)
            s.flush()
            first.setdefault("study", study.id)
            member = next(e for e in made_experiments if e.batch_id == made.id)
            s.add_all(
                [
                    StudyItem(study_id=study.id, kind="batch", item_id=made.id),
                    StudyItem(study_id=study.id, kind="experiment", item_id=member.id),
                    StudyItem(study_id=study.id, kind="analysis", item_id=analysis.id),
                    Note(kind="study", item_id=study.id, body="About the study"),
                    Note(kind="experiment", item_id=member.id, body="About a run"),
                ]
            )
        s.commit()
        return first


ENDPOINTS = [
    "/experiments",
    "/experiments/{experiment}",
    "/experiments/{experiment}/executions",
    "/batches",
    "/batches/{batch}",
    "/executions",
    "/executions/{execution}",
    "/executions/{execution}/trace",
    "/agents",
    "/agent-teams",
    "/analyses",
    "/analyses/executions",
    "/studies",
    "/studies/{study}",
    "/studies/{study}/activity",
    "/studies/memberships?kind=experiment",
    "/prompts",
    "/prompt-versions",
    "/dashboard",
    "/agents/{agent}/output-paths",
]


def queries_of(client, engine, path_template: str, ids: dict) -> int:
    path = path_template.format(**ids)
    with counting(engine) as statements:
        response = client.get(path)
    assert response.status_code == 200, (path, response.text)
    return len(statements)


@pytest.mark.parametrize("path", ENDPOINTS)
def test_a_bigger_workspace_does_not_cost_more_queries(client, engine, path):
    small_ids = populate(engine, experiments=2, agents=1, batch_size=2)
    small = queries_of(client, engine, path, small_ids)

    big_ids = populate(engine, experiments=8, agents=4, batch_size=4)
    big = queries_of(client, engine, path, big_ids)

    assert big == small, f"{path}: {small} queries on 2 experiments, {big} on 10"


def test_computing_an_analysis_does_not_cost_more_queries_per_run(client, engine):
    def compute(ids) -> int:
        body = {
            "config": {
                "truth_column": "truth",
                "value_type": "numeric",
                "metrics": ["mae"],
            },
            "runs": [
                {"execution_id": execution, "agent_name": "Agent 0"}
                for execution in ids["executions"]
            ],
        }
        with counting(engine) as statements:
            response = client.post("/analyses/compute", json=body)
        assert response.status_code == 200, response.text
        return len(statements)

    small = compute(populate(engine, experiments=1, agents=1))
    big = compute(populate(engine, experiments=8, agents=1))

    assert big == small
