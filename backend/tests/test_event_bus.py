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

import event_bus
from schemas.events import RunEvent, RunState


def progress(rows_done: int) -> RunEvent:
    state = RunState(experiment_id=1, status="running", rows_done=rows_done)
    return RunEvent(name="progress", state=state, workspace_id=1)


def drain(queue) -> list[int]:
    done = []
    while not queue.empty():
        done.append(queue.get_nowait().state.rows_done)
    return done


def test_every_subscriber_receives_every_event():
    with event_bus.subscribe() as first, event_bus.subscribe() as second:
        event_bus.publish(progress(1))
        event_bus.publish(progress(2))

        assert drain(first) == [1, 2]
        assert drain(second) == [1, 2]


def test_leaving_the_context_unsubscribes():
    with event_bus.subscribe() as queue:
        pass

    event_bus.publish(progress(1))

    assert queue.empty()


def test_full_queue_drops_its_oldest_events(monkeypatch):
    monkeypatch.setattr(event_bus, "QUEUE_SIZE", 2)

    with event_bus.subscribe() as queue:
        for rows_done in (1, 2, 3):
            event_bus.publish(progress(rows_done))

        assert drain(queue) == [2, 3]


def test_events_published_from_a_thread_reach_a_subscriber_on_the_loop():
    import asyncio
    import threading

    async def scenario():
        with event_bus.subscribe() as queue:
            thread = threading.Thread(target=event_bus.publish, args=(progress(7),))
            thread.start()
            thread.join()
            return (await asyncio.wait_for(queue.get(), timeout=1)).state.rows_done

    assert asyncio.run(scenario()) == 7
