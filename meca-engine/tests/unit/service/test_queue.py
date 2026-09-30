"""Unit tests for meca_engine.service.queue."""

from __future__ import annotations

import pytest

from meca_engine.service.job import Job
from meca_engine.service.queue import JobQueue

pytestmark = pytest.mark.unit


def test_new_queue_is_empty() -> None:
    queue = JobQueue()

    assert queue.empty() is True
    assert queue.size() == 0
    assert queue.dequeue() is None


def test_fifo_order() -> None:
    queue = JobQueue()
    first = Job(article_id="a")
    second = Job(article_id="b")

    queue.enqueue(first)
    queue.enqueue(second)

    assert queue.size() == 2
    assert queue.dequeue() is first
    assert queue.dequeue() is second
    assert queue.empty() is True
