"""Unit tests for meca_engine.orchestrator.queue_prep."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from meca_engine.checkpoint.backends.in_memory import InMemoryCheckpointStore
from meca_engine.checkpoint.models import ArticleStage
from meca_engine.orchestrator.queue_prep import already_complete, prepare_queue

if TYPE_CHECKING:
    from collections.abc import Callable

    from meca_engine.input.models import ArticleReference

pytestmark = pytest.mark.unit


def test_prepare_queue_sorts_deterministically(
    make_article_reference: Callable[[str], ArticleReference],
) -> None:
    store = InMemoryCheckpointStore()
    refs = (make_article_reference("ART-0002"), make_article_reference("ART-0001"))

    queue = prepare_queue(refs, store)

    assert [r.article_id for r in queue] == ["ART-0001", "ART-0002"]


def test_prepare_queue_excludes_already_staged(
    make_article_reference: Callable[[str], ArticleReference],
) -> None:
    store = InMemoryCheckpointStore()
    store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGING)
    store.transition(
        "ART-0001", expected_current=ArticleStage.STAGING, new_stage=ArticleStage.STAGED
    )
    refs = (make_article_reference("ART-0001"), make_article_reference("ART-0002"))

    queue = prepare_queue(refs, store)

    assert [r.article_id for r in queue] == ["ART-0002"]


def test_prepare_queue_includes_failed_articles_for_retry(
    make_article_reference: Callable[[str], ArticleReference],
) -> None:
    store = InMemoryCheckpointStore()
    store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGING)
    store.transition(
        "ART-0001",
        expected_current=ArticleStage.STAGING,
        new_stage=ArticleStage.FAILED,
        failure_reason="boom",
    )
    refs = (make_article_reference("ART-0001"),)

    queue = prepare_queue(refs, store)

    assert [r.article_id for r in queue] == ["ART-0001"]


def test_already_complete_is_the_complement_of_prepare_queue(
    make_article_reference: Callable[[str], ArticleReference],
) -> None:
    store = InMemoryCheckpointStore()
    store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGING)
    store.transition(
        "ART-0001", expected_current=ArticleStage.STAGING, new_stage=ArticleStage.STAGED
    )
    refs = (make_article_reference("ART-0001"), make_article_reference("ART-0002"))

    queue = prepare_queue(refs, store)
    complete = already_complete(refs, store)

    assert {r.article_id for r in queue} | {r.article_id for r in complete} == {
        "ART-0001",
        "ART-0002",
    }
    assert {r.article_id for r in queue} & {r.article_id for r in complete} == set()
