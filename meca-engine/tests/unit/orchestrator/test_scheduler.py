"""Unit tests for meca_engine.orchestrator.scheduler."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from meca_engine.checkpoint.models import ArticleStage
from meca_engine.orchestrator.models import ArticleOutcome, OutcomeStatus
from meca_engine.orchestrator.scheduler import SequentialWorkerScheduler

if TYPE_CHECKING:
    from collections.abc import Callable

    from meca_engine.input.models import ArticleReference

pytestmark = pytest.mark.unit


def test_processes_tasks_in_input_order(
    make_article_reference: Callable[[str], ArticleReference],
) -> None:
    scheduler = SequentialWorkerScheduler()
    tasks = [make_article_reference("ART-0002"), make_article_reference("ART-0001")]
    processed_order: list[str] = []

    def task_fn(ref: ArticleReference) -> ArticleOutcome:
        processed_order.append(ref.article_id)
        return ArticleOutcome(
            article_id=ref.article_id,
            status=OutcomeStatus.SUCCESS,
            stage_reached=ArticleStage.STAGED,
        )

    outcomes = list(scheduler.schedule(tasks, task_fn))

    assert processed_order == ["ART-0002", "ART-0001"]
    assert [o.article_id for o in outcomes] == ["ART-0002", "ART-0001"]


def test_empty_task_list_yields_nothing() -> None:
    scheduler = SequentialWorkerScheduler()

    outcomes = list(scheduler.schedule([], lambda ref: pytest.fail("should not be called")))

    assert outcomes == []
