"""Unit tests for meca_engine.orchestrator.models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from meca_engine.checkpoint.models import ArticleStage
from meca_engine.orchestrator.models import ArticleOutcome, OutcomeStatus, RunSummary

pytestmark = pytest.mark.unit


def _outcome(status: OutcomeStatus) -> ArticleOutcome:
    return ArticleOutcome(article_id="ART-0001", status=status, stage_reached=ArticleStage.STAGED)


def test_run_summary_counts_by_status() -> None:
    now = datetime.now(timezone.utc)
    summary = RunSummary(
        batch_id="b1",
        run_id="r1",
        started_at=now,
        completed_at=now,
        total_discovered=3,
        total_discovery_failures=0,
        outcomes=(
            _outcome(OutcomeStatus.SUCCESS),
            _outcome(OutcomeStatus.SUCCESS),
            _outcome(OutcomeStatus.FAILED),
            _outcome(OutcomeStatus.SKIPPED),
        ),
    )

    assert summary.succeeded_count == 2
    assert summary.failed_count == 1
    assert summary.skipped_count == 1


def test_run_summary_counts_are_zero_for_empty_outcomes() -> None:
    now = datetime.now(timezone.utc)
    summary = RunSummary(
        batch_id="b1",
        run_id="r1",
        started_at=now,
        completed_at=now,
        total_discovered=0,
        total_discovery_failures=0,
        outcomes=(),
    )

    assert summary.succeeded_count == 0
    assert summary.failed_count == 0
    assert summary.skipped_count == 0
