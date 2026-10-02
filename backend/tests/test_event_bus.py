import event_bus
from schemas.events import RunEvent, RunState


def progress(rows_done: int) -> RunEvent:
    state = RunState(experiment_id=1, status="running", rows_done=rows_done)
    return RunEvent(name="progress", state=state)


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
