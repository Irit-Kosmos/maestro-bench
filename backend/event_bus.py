"""
In-process pub/sub behind the live run stream.

Subscribers live on uvicorn's event loop, one queue each. Events can be published
from the loop or from a worker thread (a route that cancels a queued run, for
instance): from a thread they are handed to the subscriber's loop. It only works
with a single worker process.

Events are published once their state is committed, and each carries the whole
state of its execution: a subscriber that falls behind loses the oldest events
without ever holding a wrong state.
"""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager

from schemas.events import RunEvent

QUEUE_SIZE = 1024

# Each queue with the loop it is read on (None when subscribed outside any loop)
_subscribers: dict[asyncio.Queue[RunEvent], asyncio.AbstractEventLoop | None] = {}


def _running_loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


def _put(queue: asyncio.Queue[RunEvent], event: RunEvent) -> None:
    if queue.full():
        queue.get_nowait()
    queue.put_nowait(event)


def publish(event: RunEvent) -> None:
    here = _running_loop()
    for queue, loop in list(_subscribers.items()):
        if loop is None or loop is here:
            _put(queue, event)
        else:
            try:
                loop.call_soon_threadsafe(_put, queue, event)
            except RuntimeError:
                # The loop is closed: nobody reads this queue any more
                _subscribers.pop(queue, None)


@contextmanager
def subscribe() -> Iterator[asyncio.Queue[RunEvent]]:
    queue: asyncio.Queue[RunEvent] = asyncio.Queue(maxsize=QUEUE_SIZE)
    _subscribers[queue] = _running_loop()
    try:
        yield queue
    finally:
        _subscribers.pop(queue, None)
