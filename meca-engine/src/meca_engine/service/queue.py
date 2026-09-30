"""In-memory FIFO job queue — no external broker, matching current sequential-only scale."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meca_engine.service.job import Job


class JobQueue:
    """A pure in-memory, first-in-first-out queue of :class:`~meca_engine.service.job.Job`."""

    def __init__(self) -> None:
        """Initialize an empty queue."""
        self._items: deque[Job] = deque()

    def enqueue(self, job: Job) -> None:
        """Add a job to the back of the queue."""
        self._items.append(job)

    def dequeue(self) -> Job | None:
        """Remove and return the job at the front of the queue, or ``None`` if empty."""
        if not self._items:
            return None
        return self._items.popleft()

    def size(self) -> int:
        """Return the number of jobs currently queued."""
        return len(self._items)

    def empty(self) -> bool:
        """Return whether the queue currently holds no jobs."""
        return not self._items
