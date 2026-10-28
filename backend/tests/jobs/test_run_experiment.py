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

"""A whole run, with the LLM calls stubbed out: its work is done off the event loop."""

import asyncio
import json
import threading

import pytest
from sqlmodel import Session, select

import async_jobs
import event_bus
from core.orchestrator import PipelineResult
from experiment_utils import add_experiment
from schemas.experiments import ExperimentCreate
from tables import (
    Agent,
    Dataset,
    Experiment,
    ExperimentExecution,
    Model,
    Prompt,
    PromptVersion,
    User,
)
from tests.conftest import scoped

ROWS = 12


@pytest.fixture
def experiment_id(engine, datasets_dir, monkeypatch):
    monkeypatch.setattr(async_jobs, "engine", engine)
    (datasets_dir / "answers.csv").write_text(
        "id,text\n" + "".join(f"{i},row {i}\n" for i in range(ROWS))
    )
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        prompt = Prompt(name="Grader")
        model = Model(name="m", provider="ollama")
        s.add_all([dataset, prompt, model])
        s.flush()
        version = PromptVersion(
            prompt_id=prompt.id, version="1", user_prompt="{{ answer }}"
        )
        s.add(version)
        s.flush()
        agent = Agent(
            name="Grader",
            default_prompt_version_id=version.id,
            default_model_id=model.id,
        )
        s.add(agent)
        s.flush()
        experiment = add_experiment(
            s,
            ExperimentCreate(
                name="Run",
                dataset_id=dataset.id,
                agent_configurations={
                    str(agent.id): {
                        "is_active": True,
                        "prompt_version_id": version.id,
                        "model_id": model.id,
                        "input_mappings": [
                            {
                                "variable": "answer",
                                "source": "dataset",
                                "sourceColumn": "text",
                            }
                        ],
                    }
                },
                sampling_type="all",
            ),
        )
        s.commit()
        return experiment.id


@pytest.fixture
def pipeline(monkeypatch):
    async def run_pipeline(agents, row, row_index=0, dataset_row_id=None):
        await asyncio.sleep(0.01)
        return PipelineResult(
            row_index=row_index,
            input_data=row,
            dataset_row_id=dataset_row_id,
            final_output="ok",
        )

    monkeypatch.setattr(async_jobs, "run_pipeline", run_pipeline)


def test_a_run_completes_and_writes_its_results(engine, experiment_id, pipeline):
    async def scenario():
        with event_bus.subscribe() as events:
            await async_jobs.run_experiment_async(experiment_id)
            names = []
            while not events.empty():
                event = events.get_nowait()
                names.append((event.name, event.state.status, event.state.rows_done))
        return names

    published = asyncio.run(scenario())

    with scoped(engine) as s:
        experiment = s.get(Experiment, experiment_id)
        execution = s.exec(select(ExperimentExecution)).one()
    assert experiment.status == "completed"
    assert (execution.status, execution.rows_done, execution.rows_total) == (
        "completed",
        ROWS,
        ROWS,
    )
    assert execution.results_file_path
    assert published[0][:2] == ("status", "running")
    assert published[-1][:2] == ("status", "completed")
    assert max(done for _, _, done in published) == ROWS


def test_the_progress_is_written_off_the_event_loop(
    engine, experiment_id, pipeline, monkeypatch
):
    # Which thread does each write run on? Measuring how long the loop stalls
    # would say the same, but depends on how loaded the machine is
    real_commit = async_jobs._RunProgress._commit
    writers = []

    def spying_commit(self, state):
        writers.append(threading.get_ident())
        real_commit(self, state)

    monkeypatch.setattr(async_jobs._RunProgress, "_commit", spying_commit)

    async def scenario():
        await async_jobs.run_experiment_async(experiment_id)
        return threading.get_ident()

    loop_thread = asyncio.run(scenario())

    assert writers
    assert loop_thread not in writers


def test_cancelling_a_run_closes_it_as_cancelled(engine, experiment_id, monkeypatch):
    started = asyncio.Event()

    async def run_pipeline(agents, row, row_index=0, dataset_row_id=None):
        started.set()
        await asyncio.sleep(30)

    monkeypatch.setattr(async_jobs, "run_pipeline", run_pipeline)

    async def scenario():
        task = asyncio.create_task(async_jobs.run_experiment_async(experiment_id))
        await asyncio.wait_for(started.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())

    with scoped(engine) as s:
        assert s.get(Experiment, experiment_id).status == "cancelled"
        execution = s.exec(select(ExperimentExecution)).one()
    assert execution.status == "cancelled"
    assert execution.completed_at is not None


def test_a_failing_setup_marks_the_run_failed(engine, experiment_id, datasets_dir):
    (datasets_dir / "answers.csv").unlink()

    asyncio.run(async_jobs.run_experiment_async(experiment_id))

    with scoped(engine) as s:
        assert s.get(Experiment, experiment_id).status == "failed"


def test_results_are_valid_json(engine, experiment_id, pipeline, results_dir):
    asyncio.run(async_jobs.run_experiment_async(experiment_id))

    (path,) = results_dir.glob("*_results.json")
    assert len(json.loads(path.read_text())["rows"]) == ROWS


def test_no_transaction_is_left_open_while_the_run_waits_for_its_rows(
    engine, experiment_id
):
    with Session(engine) as session:
        run = async_jobs._begin_run(session, experiment_id)

        assert run is not None
        assert not session.in_transaction()


def test_the_execution_records_who_launched_it(engine, experiment_id, pipeline):
    with Session(engine, expire_on_commit=False) as db:
        user = User(display_name="Alice")
        db.add(user)
        db.commit()
    # What `start_experiment` leaves for the run, as the route that launched it asked
    async_jobs._launched_by[experiment_id] = user.id

    asyncio.run(async_jobs.run_experiment_async(experiment_id))

    with Session(engine) as session:
        execution = session.exec(select(ExperimentExecution)).one()
        assert execution.created_by == user.id
    assert experiment_id not in async_jobs._launched_by
