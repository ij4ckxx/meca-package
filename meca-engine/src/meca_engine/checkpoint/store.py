"""Checkpoint Store abstract interface.

Per 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.12: atomic per-article
state read/compare-and-set, enabling restart-without-reprocessing
(ADR-022) and preventing duplicate-dispatch under concurrent processing
(Test Specification TC-183). Milestone 2 provides only the in-memory
backend (:mod:`meca_engine.checkpoint.backends.in_memory`); a durable
backend (Postgres/DynamoDB, per 16_LLD_07_READINESS_ASSESSMENT.md §15.2
TQ-03) is deferred to the milestone that needs cross-run durability in
production.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from meca_engine.checkpoint.models import ArticleStage, CheckpointRecord, stage_index


class CheckpointStore(ABC):
    """Durable (or, for Milestone 2, in-memory), atomic per-article state store.

    Every state transition is a compare-and-set: the caller states what
    stage it *expects* the article to currently be in, and the store only
    applies the transition if that expectation holds — this is what
    prevents two workers from processing the same article simultaneously
    (13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md §9.5).
    """

    @abstractmethod
    def get_record(self, article_id: str) -> CheckpointRecord | None:
        """Return the current checkpoint record for an article, if any.

        Args:
            article_id: The article to look up.

        Returns:
            The article's :class:`~meca_engine.checkpoint.models.CheckpointRecord`,
            or ``None`` if no record exists yet (equivalent to
            ``ArticleStage.NOT_STARTED``).
        """

    @abstractmethod
    def transition(
        self,
        article_id: str,
        *,
        expected_current: ArticleStage | None,
        new_stage: ArticleStage,
        failure_reason: str | None = None,
    ) -> bool:
        """Atomically move an article to a new stage, if its current stage matches.

        Args:
            article_id: The article to transition.
            expected_current: The stage the caller expects the article to
                currently be in, or ``None`` to mean "no record must exist
                yet" (used for the very first transition of an article).
            new_stage: The stage to move the article to.
            failure_reason: A short description of what failed; only
                meaningful when ``new_stage`` is ``ArticleStage.FAILED``.

        Returns:
            ``True`` if the transition was applied; ``False`` if the
            article's actual current stage did not match
            ``expected_current`` (someone else already moved it, or it
            already exists when the caller expected it not to) — callers
            must treat ``False`` as "abandon this attempt, another worker
            owns this article" rather than an error.
        """

    @abstractmethod
    def list_all(self) -> tuple[CheckpointRecord, ...]:
        """Return every checkpoint record currently known to the store.

        Returns:
            All records, in no particular guaranteed order.
        """

    def is_at_least(self, article_id: str, minimum_stage: ArticleStage) -> bool:
        """Return whether an article has reached at least the given stage.

        Used for resume support: an article already at or past
        ``minimum_stage`` should be skipped on a resumed run rather than
        reprocessed from scratch (ADR-022).

        Args:
            article_id: The article to check.
            minimum_stage: The stage threshold to compare against. Must
                not be ``ArticleStage.FAILED``.

        Returns:
            ``True`` if the article has a record whose stage's position
            in :data:`~meca_engine.checkpoint.models.STAGE_ORDER` is at or
            beyond ``minimum_stage``'s position. A ``FAILED`` article
            always returns ``False`` (a failed article has not "reached"
            any forward stage — it must be retried from the start).
        """
        record = self.get_record(article_id)
        if record is None:
            return False
        if record.stage is ArticleStage.FAILED:
            return False
        return stage_index(record.stage) >= stage_index(minimum_stage)
