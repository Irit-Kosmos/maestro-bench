"""
In-process pub/sub behind the live run stream.

Runs and subscribers share uvicorn's event loop, so a queue per subscriber is
enough. It only works with a single worker process.

Events are published once their state is committed, and each carries the whole
state of its execution: a subscriber that falls behind loses the oldest events
without ever holding a wrong state.
"""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager

from schemas.events import RunEvent

QUEUE_SIZE = 1024

_subscribers: set[asyncio.Queue[RunEvent]] = set()


def publish(event: RunEvent) -> None:
    for queue in _subscribers:
        if queue.full():
            queue.get_nowait()
        queue.put_nowait(event)


@contextmanager
def subscribe() -> Iterator[asyncio.Queue[RunEvent]]:
    queue: asyncio.Queue[RunEvent] = asyncio.Queue(maxsize=QUEUE_SIZE)
    _subscribers.add(queue)
    try:
        yield queue
    finally:
        _subscribers.discard(queue)
