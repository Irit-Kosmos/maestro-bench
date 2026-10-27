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

import pytest

import event_bus
from async_jobs import _RunProgress
from tables import Dataset, Experiment, ExperimentExecution


@pytest.fixture
def execution(session):
    dataset = Dataset(name="answers", file_path="answers.csv")
    session.add(dataset)
    session.flush()
    experiment = Experiment(name="Run", dataset_id=dataset.id)
    session.add(experiment)
    session.flush()
    execution = ExperimentExecution(experiment_id=experiment.id, dataset_snapshot="{}")
    session.add(execution)
    session.commit()
    return execution


def test_rows_are_counted_in_the_database_and_published(session, execution):
    progress = _RunProgress(session, execution, batch_id=5, workspace_id=1)

    async def count():
        with event_bus.subscribe() as queue:
            await progress.start(3)
            await progress.row_done(failed=False)
            await progress.row_done(failed=True)

            return [queue.get_nowait() for _ in range(3)]

    events = asyncio.run(count())

    assert {event.name for event in events} == {"progress"}
    assert [
        (e.state.rows_total, e.state.rows_done, e.state.rows_failed) for e in events
    ] == [(3, 0, 0), (3, 1, 0), (3, 2, 1)]
    assert {e.state.batch_id for e in events} == {5}

    session.refresh(execution)
    assert (execution.rows_total, execution.rows_done, execution.rows_failed) == (
        3,
        2,
        1,
    )


def test_published_events_are_not_altered_by_later_rows(session, execution):
    progress = _RunProgress(session, execution, batch_id=None, workspace_id=1)

    async def count():
        with event_bus.subscribe() as queue:
            await progress.start(2)
            await progress.row_done(failed=False)

            return [queue.get_nowait().state.rows_done for _ in range(2)]

    assert asyncio.run(count()) == [0, 1]


def test_rows_finishing_together_are_counted_once_each(session, execution):
    progress = _RunProgress(session, execution, batch_id=None, workspace_id=1)

    async def finish_together_events():
        with event_bus.subscribe() as queue:
            await progress.start(20)
            await asyncio.gather(*(progress.row_done(failed=False) for _ in range(20)))
            events = []
            while not queue.empty():
                events.append(queue.get_nowait().state.rows_done)
            return events

    # Rows finishing during a write are covered by the next one: counts only go up
    published = asyncio.run(finish_together_events())
    assert published == sorted(published)
    assert published[-1] == 20
    session.refresh(execution)
    assert execution.rows_done == 20


def test_announce_publishes_a_status_event(session, execution):
    progress = _RunProgress(session, execution, batch_id=None, workspace_id=1)

    with event_bus.subscribe() as queue:
        progress.announce("completed")

        event = queue.get_nowait()

    assert event.name == "status"
    assert event.state.status == "completed"
    assert event.state.execution_id == execution.id
