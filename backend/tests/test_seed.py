import pytest
from sqlmodel import Session, func, select

from scripts import seed
from tables import (
    Agent,
    AgentTeam,
    Dataset,
    Experiment,
    ExperimentAgentConfig,
    Model,
    Prompt,
    PromptVersion,
    Tag,
    TagLink,
)

SEEDED = (Model, Prompt, PromptVersion, AgentTeam, Agent, Dataset, Tag, TagLink)


@pytest.fixture(autouse=True)
def seed_on_test_database(engine, monkeypatch):
    monkeypatch.setattr(seed, "engine", engine)
    monkeypatch.setattr(seed, "init_db", lambda: None)


def counts(engine) -> dict[str, int]:
    with Session(engine) as s:
        return {
            table.__name__: s.exec(select(func.count()).select_from(table)).one()
            for table in SEEDED
        }


def test_seeding_an_empty_database_creates_the_samples(engine):
    seed.seed_data()

    assert counts(engine) == {
        "Model": 4,
        "Prompt": 3,
        "PromptVersion": 3,
        "AgentTeam": 2,
        "Agent": 3,
        "Dataset": 2,
        "Tag": 2,
        "TagLink": 3,
    }


def test_seeding_twice_adds_nothing(engine):
    seed.seed_data()
    first = counts(engine)

    seed.seed_data()

    assert counts(engine) == first


def test_existing_data_is_kept_and_not_duplicated(engine):
    """A database in use: same names as the samples, plus experiments on top."""
    with Session(engine) as s:
        dataset = Dataset(name="My Mohler", file_path="mohler_dataset.csv")
        team = AgentTeam(name="Corrector", description="mine")
        model = Model(name="mistral-small-2503", provider="mistral", is_active=False)
        tag = Tag(name="Evaluation", color="red")
        s.add_all([dataset, team, model, tag])
        s.flush()
        agent = Agent(name="Language", team_id=team.id, description="mine")
        s.add(agent)
        s.flush()
        experiment = Experiment(name="Run", dataset_id=dataset.id)
        s.add(experiment)
        s.flush()
        s.add(ExperimentAgentConfig(experiment_id=experiment.id, agent_id=agent.id))
        s.commit()
        ids = {"dataset": dataset.id, "team": team.id, "agent": agent.id}

    seed.seed_data()

    with Session(engine) as s:
        # What was there is untouched...
        assert s.get(Dataset, ids["dataset"]).name == "My Mohler"
        assert s.get(AgentTeam, ids["team"]).description == "mine"
        assert s.get(Agent, ids["agent"]).description == "mine"
        assert (
            s.exec(select(Model).where(Model.name == "mistral-small-2503"))
            .one()
            .is_active
            is False
        )
        assert (
            s.exec(select(Tag).where(func.lower(Tag.name) == "evaluation")).one().color
            == "red"
        )
        assert s.exec(select(func.count()).select_from(Experiment)).one() == 1
        # ... and only the missing samples were added
        assert s.exec(select(func.count()).select_from(Dataset)).one() == 2
        assert s.exec(select(func.count()).select_from(AgentTeam)).one() == 2
        assert s.exec(select(func.count()).select_from(Agent)).one() == 3
        assert s.exec(select(func.count()).select_from(Model)).one() == 4
