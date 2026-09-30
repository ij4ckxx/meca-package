"""Unit tests for meca_engine.checkpoint.backends.in_memory.InMemoryCheckpointStore."""

from __future__ import annotations

import threading

import pytest

from meca_engine.checkpoint.backends.in_memory import InMemoryCheckpointStore
from meca_engine.checkpoint.models import ArticleStage

pytestmark = pytest.mark.unit


@pytest.fixture
def store() -> InMemoryCheckpointStore:
    return InMemoryCheckpointStore()


def test_get_record_returns_none_for_unknown_article(store: InMemoryCheckpointStore) -> None:
    assert store.get_record("ART-0001") is None


def test_first_transition_from_none_succeeds(store: InMemoryCheckpointStore) -> None:
    ok = store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGING)

    assert ok is True
    record = store.get_record("ART-0001")
    assert record is not None
    assert record.stage is ArticleStage.STAGING


def test_transition_with_wrong_expected_current_fails(store: InMemoryCheckpointStore) -> None:
    store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGING)

    ok = store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGED)

    assert ok is False
    # State unchanged.
    assert store.get_record("ART-0001").stage is ArticleStage.STAGING  # type: ignore[union-attr]


def test_transition_chain_succeeds_when_expectations_match(store: InMemoryCheckpointStore) -> None:
    assert store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGING)
    assert store.transition(
        "ART-0001", expected_current=ArticleStage.STAGING, new_stage=ArticleStage.STAGED
    )

    assert store.get_record("ART-0001").stage is ArticleStage.STAGED  # type: ignore[union-attr]


def test_failed_transition_records_failure_reason(store: InMemoryCheckpointStore) -> None:
    store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGING)
    store.transition(
        "ART-0001",
        expected_current=ArticleStage.STAGING,
        new_stage=ArticleStage.FAILED,
        failure_reason="disk full",
    )

    record = store.get_record("ART-0001")
    assert record is not None
    assert record.stage is ArticleStage.FAILED
    assert record.failure_reason == "disk full"


def test_list_all_returns_every_record(store: InMemoryCheckpointStore) -> None:
    store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGING)
    store.transition("ART-0002", expected_current=None, new_stage=ArticleStage.STAGING)

    records = store.list_all()

    assert {r.article_id for r in records} == {"ART-0001", "ART-0002"}


def test_reset_clears_all_records(store: InMemoryCheckpointStore) -> None:
    store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGING)

    store.reset()

    assert store.list_all() == ()
    assert store.get_record("ART-0001") is None


def test_is_at_least_true_when_stage_matches_or_exceeds(store: InMemoryCheckpointStore) -> None:
    store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGING)
    store.transition(
        "ART-0001", expected_current=ArticleStage.STAGING, new_stage=ArticleStage.STAGED
    )

    assert store.is_at_least("ART-0001", ArticleStage.STAGING) is True
    assert store.is_at_least("ART-0001", ArticleStage.STAGED) is True
    assert store.is_at_least("ART-0001", ArticleStage.METADATA_LOADED) is False


def test_is_at_least_false_for_unknown_article(store: InMemoryCheckpointStore) -> None:
    assert store.is_at_least("ART-UNKNOWN", ArticleStage.NOT_STARTED) is False


def test_is_at_least_false_for_failed_article(store: InMemoryCheckpointStore) -> None:
    store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGING)
    store.transition(
        "ART-0001",
        expected_current=ArticleStage.STAGING,
        new_stage=ArticleStage.FAILED,
        failure_reason="boom",
    )

    assert store.is_at_least("ART-0001", ArticleStage.NOT_STARTED) is False


def test_concurrent_transitions_are_serialized_and_exactly_one_wins(
    store: InMemoryCheckpointStore,
) -> None:
    store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGING)

    results: list[bool] = []
    lock = threading.Lock()

    def attempt() -> None:
        ok = store.transition(
            "ART-0001", expected_current=ArticleStage.STAGING, new_stage=ArticleStage.STAGED
        )
        with lock:
            results.append(ok)

    threads = [threading.Thread(target=attempt) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count(True) == 1
    assert results.count(False) == 9
