"""A team with the three roles, a workspace full of things to share, and an anonymous reader."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

import main
import workspace_files
from tables import (
    Analysis,
    Batch,
    Dataset,
    Experiment,
    ExperimentExecution,
    Note,
    Study,
    StudyItem,
    Tag,
    TagLink,
    Workspace,
)
from tests.auth.conftest import alice, app, auth_config, bob  # noqa: F401
from tests.auth.people import Person, add_member
from workspace_scope import scope_session

ROWS = [
    {
        "row_index": 1,
        "input_data": {"text": "great", "author": "Dr Who", "file_path": "x.csv", "score": 5},
        "agents": [{"name": "Grader", "output": '{"score": 4}', "error": None}],
    }
]


@pytest.fixture
def carol(engine, app):  # noqa: F811
    return Person(engine, "carol")


@pytest.fixture
def team(alice, bob, carol, engine):  # noqa: F811
    """alice owns it, bob edits, carol only reads."""
    slug = alice.create_workspace("Team")
    add_member(engine, slug, bob, "editor")
    add_member(engine, slug, carol, "viewer")
    return slug


@pytest.fixture
def reader(app):  # noqa: F811
    """Someone with no account and no cookie."""
    return TestClient(main.app)


def workspace_id(engine, slug: str) -> int:
    with Session(engine) as db:
        return db.exec(select(Workspace.id).where(Workspace.slug == slug)).one()


def build_world(engine, slug: str, author_id: int) -> dict[str, int]:
    """What a workspace holds, with the people, tags and notes a link must not show.

    A batch with one experiment (derived from `base`), a lone experiment `solo`, an
    experiment `other` that nothing gathers, an analysis comparing solo's execution,
    and a study gathering the batch and the analysis.
    """
    ws = workspace_id(engine, slug)
    results = workspace_files.results_dir(ws)
    results.mkdir(parents=True, exist_ok=True)
    (results / "rows.json").write_text(json.dumps({"rows": ROWS}))

    with Session(engine) as db:
        scope_session(db, ws, author_id)
        dataset = Dataset(name="answers", file_path="private/answers.csv")
        db.add(dataset)
        db.flush()

        def experiment(name, batch_id=None):
            row = Experiment(name=name, dataset_id=dataset.id, batch_id=batch_id)
            db.add(row)
            db.flush()
            execution = ExperimentExecution(
                experiment_id=row.id,
                status="completed",
                dataset_snapshot=json.dumps(
                    {"id": dataset.id, "name": "answers", "file_path": "private/answers.csv"}
                ),
                results_file_path="rows.json",
            )
            db.add(execution)
            db.flush()
            return row.id, execution.id

        base, _ = experiment("Base")
        batch = Batch(name="Grid", base_experiment_id=base)
        db.add(batch)
        db.flush()
        member, member_run = experiment("Grid member", batch.id)
        solo, solo_run = experiment("Solo")
        other, other_run = experiment("Other")

        analysis = Analysis(
            name="Agreement",
            config=json.dumps(
                {
                    "truth_column": "score",
                    "output_path": "score",
                    "value_type": "numeric",
                    "metrics": ["mae"],
                    "n_boot": 10,
                }
            ),
            runs=json.dumps([{"execution_id": solo_run, "agent_name": "Grader", "label": "a"}]),
        )
        study = Study(name="Prompt v3", description="Why we did it")
        tag = Tag(name="secret-wip")
        db.add_all([analysis, study, tag])
        db.flush()
        db.add_all(
            [
                StudyItem(study_id=study.id, kind="batch", item_id=batch.id, added_by=author_id),
                StudyItem(study_id=study.id, kind="analysis", item_id=analysis.id, added_by=author_id),
                TagLink(tag_id=tag.id, kind="study", item_id=study.id),
                TagLink(tag_id=tag.id, kind="analysis", item_id=analysis.id),
                Note(kind="study", item_id=study.id, body="PRIVATE NOTE"),
                Note(kind="experiment", item_id=solo, body="PRIVATE NOTE"),
            ]
        )
        db.commit()
        return {
            "base": base,
            "batch": batch.id,
            "member": member,
            "member_run": member_run,
            "solo": solo,
            "solo_run": solo_run,
            "other": other,
            "other_run": other_run,
            "analysis": analysis.id,
            "study": study.id,
        }


def share(person, slug: str, kind: str, item_id: int) -> str:
    """The token of the link an editor makes."""
    response = person.post(f"/workspaces/{slug}/shares", json={"kind": kind, "item_id": item_id})
    assert response.status_code in (200, 201), response.text
    return response.json()["token"]
