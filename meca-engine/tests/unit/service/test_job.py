"""Unit tests for meca_engine.service.job."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from meca_engine.service.job import Job, JobStatus

pytestmark = pytest.mark.unit


def test_job_defaults() -> None:
    job = Job(article_id="cs-2025-0001")

    assert job.article_id == "cs-2025-0001"
    assert job.job_id
    assert job.status is JobStatus.PENDING
    assert job.retry_count == 0
    assert job.duration_seconds is None


def test_job_ids_are_unique() -> None:
    assert Job(article_id="a").job_id != Job(article_id="a").job_id


def test_duration_seconds_computed_once_both_timestamps_set() -> None:
    job = Job(article_id="cs-2025-0001")
    job.started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    job.finished_at = job.started_at + timedelta(seconds=5)

    assert job.duration_seconds == 5.0
