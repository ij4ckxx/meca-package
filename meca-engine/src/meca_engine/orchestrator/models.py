"""Orchestrator-level outcome models.

Per-article and per-run results produced by
:class:`~meca_engine.orchestrator.run_controller.RunController`. Distinct
from the input-layer models (:mod:`meca_engine.input.models`) — these
describe *what happened while processing*, not the article's own content.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from meca_engine.checkpoint.models import ArticleStage
    from meca_engine.input.models import StagedArticle


@unique
class OutcomeStatus(str, Enum):
    """The terminal disposition of one article within one run."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ArticleOutcome:
    """The result of processing (or skipping) one article within one run.

    Attributes:
        article_id: The article this outcome describes.
        status: Whether the article succeeded, failed, or was skipped.
        stage_reached: The last checkpoint stage recorded for this article.
        staged_article: The resulting staged article, present only when
            ``status`` is ``SUCCESS``.
        error_message: A human-readable failure description, present only
            when ``status`` is ``FAILED``.
        exception_type: The ``type(...).__name__`` of the exception that
            caused a failure, present only when ``status`` is ``FAILED``.
    """

    article_id: str
    status: OutcomeStatus
    stage_reached: ArticleStage
    staged_article: StagedArticle | None = None
    error_message: str | None = None
    exception_type: str | None = None


@dataclass(frozen=True)
class RunSummary:
    """The aggregate result of one full batch run.

    Attributes:
        batch_id: The batch identifier this run processed.
        run_id: The unique id of this specific run (workspace-scoping id,
            also used as the structured-logging correlation id).
        started_at: When the run began.
        completed_at: When the run finished (successfully or not).
        total_discovered: Total number of article ids seen during
            discovery (both successfully-discovered and discovery-failed).
        total_discovery_failures: Number of articles that failed
            structural discovery-time validation.
        outcomes: One :class:`ArticleOutcome` per article that reached the
            scheduling/staging stage (does not include discovery-time
            failures, which are counted separately — see
            ``total_discovery_failures``).
    """

    batch_id: str
    run_id: str
    started_at: datetime
    completed_at: datetime
    total_discovered: int
    total_discovery_failures: int
    outcomes: tuple[ArticleOutcome, ...]

    @property
    def succeeded_count(self) -> int:
        """Return how many outcomes were successful."""
        return sum(1 for o in self.outcomes if o.status is OutcomeStatus.SUCCESS)

    @property
    def failed_count(self) -> int:
        """Return how many outcomes failed."""
        return sum(1 for o in self.outcomes if o.status is OutcomeStatus.FAILED)

    @property
    def skipped_count(self) -> int:
        """Return how many outcomes were skipped (already complete on resume)."""
        return sum(1 for o in self.outcomes if o.status is OutcomeStatus.SKIPPED)
