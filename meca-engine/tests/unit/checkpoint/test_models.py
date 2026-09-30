"""Unit tests for meca_engine.checkpoint.models."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import pytest

from meca_engine.checkpoint.models import STAGE_ORDER, ArticleStage, CheckpointRecord, stage_index

pytestmark = pytest.mark.unit


def test_stage_order_starts_at_not_started_and_ends_at_archived() -> None:
    assert STAGE_ORDER[0] is ArticleStage.NOT_STARTED
    assert STAGE_ORDER[-1] is ArticleStage.ARCHIVED


def test_stage_order_excludes_failed() -> None:
    assert ArticleStage.FAILED not in STAGE_ORDER


def test_stage_index_is_monotonic() -> None:
    indices = [stage_index(stage) for stage in STAGE_ORDER]

    assert indices == sorted(indices)
    assert len(set(indices)) == len(indices)


def test_stage_index_raises_for_failed() -> None:
    with pytest.raises(ValueError):
        stage_index(ArticleStage.FAILED)


def test_staged_is_between_staging_and_metadata_loaded() -> None:
    assert stage_index(ArticleStage.STAGING) < stage_index(ArticleStage.STAGED)
    assert stage_index(ArticleStage.STAGED) < stage_index(ArticleStage.METADATA_LOADED)


def test_checkpoint_record_is_frozen() -> None:
    record = CheckpointRecord(
        article_id="ART-0001", stage=ArticleStage.STAGED, updated_at=datetime.now(timezone.utc)
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        record.stage = ArticleStage.FAILED  # type: ignore[misc]


def test_checkpoint_record_failure_reason_defaults_to_none() -> None:
    record = CheckpointRecord(
        article_id="ART-0001", stage=ArticleStage.STAGED, updated_at=datetime.now(timezone.utc)
    )

    assert record.failure_reason is None
