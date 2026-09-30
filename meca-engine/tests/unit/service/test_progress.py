"""Unit tests for meca_engine.service.progress."""

from __future__ import annotations

import pytest

from meca_engine.service.progress import ProgressTracker

pytestmark = pytest.mark.unit


def test_initial_snapshot() -> None:
    tracker = ProgressTracker(total=4)
    snapshot = tracker.snapshot()

    assert snapshot.total == 4
    assert snapshot.completed == 0
    assert snapshot.remaining == 4
    assert snapshot.percentage == 0.0
    assert snapshot.estimated_remaining_seconds is None
    assert snapshot.finished_at is None


def test_progress_after_completions() -> None:
    tracker = ProgressTracker(total=2)
    tracker.start_job("a")
    tracker.complete_job()

    snapshot = tracker.snapshot()
    assert snapshot.completed == 1
    assert snapshot.remaining == 1
    assert snapshot.percentage == 50.0
    assert snapshot.estimated_remaining_seconds is not None


def test_finish_sets_finished_at() -> None:
    tracker = ProgressTracker(total=1)
    tracker.finish()

    assert tracker.snapshot().finished_at is not None


def test_zero_total_reports_full_percentage() -> None:
    tracker = ProgressTracker(total=0)

    assert tracker.snapshot().percentage == 100.0
