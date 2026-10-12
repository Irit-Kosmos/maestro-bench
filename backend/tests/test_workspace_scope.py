"""A scoped session only sees, and only writes, its own workspace."""

import pytest
from sqlalchemy import text
from sqlmodel import Session, col, delete, func, select

from tables import (
    Agent,
    Dataset,
    Experiment,
    Model,
    Prompt,
    PromptVersion,
    Tag,
    TagLink,
)
from tests.conftest import scoped
from workspace_scope import scope_session


@pytest.fixture
def two_workspaces(engine):
    """Workspace 1 (the test one) and a second one, each with a model, an agent and a prompt with a version."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO workspace (slug, name, created_at) "
                "VALUES ('other', 'Other', now())"
            )
        )
    ids = {}
    for workspace_id in (1, 2):
        with scoped(engine, workspace_id) as s:
            model = Model(name=f"model-{workspace_id}", provider="mistral")
            prompt = Prompt(name=f"prompt-{workspace_id}")
            s.add_all([model, prompt])
            s.flush()
            s.add(Agent(name=f"agent-{workspace_id}", default_model_id=model.id))
            s.add(PromptVersion(prompt_id=prompt.id, version=f"v-{workspace_id}"))
            s.commit()
            ids[workspace_id] = {"model": model.id, "prompt": prompt.id}
    return ids


def test_rows_are_stamped_with_the_session_workspace(engine, two_workspaces):
    with scoped(engine, 2) as s:
        assert s.exec(select(Model.workspace_id)).all() == [2]
        assert s.exec(select(Agent.workspace_id)).all() == [2]


def test_a_query_only_returns_the_workspace_rows(engine, two_workspaces):
    with scoped(engine, 1) as s:
        assert [m.name for m in s.exec(select(Model)).all()] == ["model-1"]
        assert [p.name for p in s.exec(select(Prompt)).all()] == ["prompt-1"]


def test_get_does_not_find_another_workspace_row(engine, two_workspaces):
    with scoped(engine, 1) as s:
        assert s.get(Model, two_workspaces[1]["model"]) is not None
        assert s.get(Model, two_workspaces[2]["model"]) is None


def test_a_filter_cannot_lift_the_scope(engine, two_workspaces):
    with scoped(engine, 1) as s:
        found = s.exec(
            select(Model).where(Model.id == two_workspaces[2]["model"])
        ).all()
        assert found == []


def test_joins_stay_in_the_workspace(engine, two_workspaces):
    with scoped(engine, 1) as s:
        rows = s.exec(
            select(Agent.name, Model.name).join(
                Model, col(Model.id) == col(Agent.default_model_id)
            )
        ).all()
        assert rows == [("agent-1", "model-1")]


def test_relationships_stay_in_the_workspace(engine, two_workspaces):
    with scoped(engine, 1) as s:
        prompt = s.exec(select(Prompt)).one()
        assert [v.version for v in prompt.versions] == ["v-1"]


def test_aggregates_stay_in_the_workspace(engine, two_workspaces):
    with scoped(engine, 1) as s:
        assert s.exec(select(func.count()).select_from(Model)).one() == 1
        assert s.exec(select(func.count(col(Model.id)))).one() == 1
        assert s.exec(select(func.min(Model.created_at))).one() is not None
        assert s.exec(select(func.count(func.distinct(col(Agent.default_model_id))))).one() == 1


def test_a_bulk_delete_only_reaches_the_workspace(engine, two_workspaces):
    with scoped(engine, 1) as s:
        s.exec(delete(Model))
        s.commit()
    with scoped(engine, 2) as s:
        assert [m.name for m in s.exec(select(Model)).all()] == ["model-2"]


def test_a_scoped_session_refuses_to_add_a_row_of_another_workspace(engine):
    with scoped(engine, 1) as s:
        s.add(Model(name="x", provider="mistral", workspace_id=2))
        with pytest.raises(RuntimeError, match="workspace 2"):
            s.flush()


def test_an_unscoped_session_cannot_add_workspace_rows(engine):
    with Session(engine) as s:
        s.add(Model(name="x", provider="mistral"))
        with pytest.raises(RuntimeError, match="scope the session first"):
            s.flush()


def test_an_unscoped_session_sees_every_workspace(engine, two_workspaces):
    with Session(engine) as s:
        assert len(s.exec(select(Model)).all()) == 2


def test_the_author_is_recorded_on_top_level_rows(engine):
    with Session(engine) as s:
        s.exec(
            text(
                'INSERT INTO "user" (display_name, is_active, created_at) '
                "VALUES ('Rémi', true, now())"
            )
        )
        s.commit()
    with Session(engine) as s:
        scope_session(s, 1, user_id=1)
        model = Model(name="x", provider="mistral")
        s.add(model)
        s.commit()
        assert model.created_by == 1


def test_child_tables_are_scoped_too(engine, two_workspaces):
    with scoped(engine, 1) as s:
        tag = Tag(name="a")
        s.add(tag)
        s.flush()
        s.add(TagLink(tag_id=tag.id, kind="prompt", item_id=1))
        s.commit()
    with scoped(engine, 2) as s:
        assert s.exec(select(TagLink)).all() == []
        assert s.exec(select(Dataset)).all() == []
        assert s.exec(select(Experiment)).all() == []
