"""Run Controller — batch lifecycle, resume support, deterministic scheduling.

Per 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.15 and the current task's
"Run Controller" requirement. Milestone 2 scope: discovery → checkpoint
resume-filtering → staging, via a deterministic (sequential)
:class:`~meca_engine.orchestrator.scheduler.WorkerScheduler`. No
transformation, generation, validation, or packaging occurs here — those
stages don't exist yet.

Per 12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §7.3's article-level vs.
batch-level distinction: an ``ArticleLevelError`` raised while staging one
article is caught here and recorded as a ``FAILED`` outcome for that
article only; a ``BatchLevelError`` (e.g. ``InsufficientDiskSpaceError``)
is deliberately allowed to propagate out of :meth:`RunController.run`
uncaught, halting the entire run.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from meca_engine.checkpoint.models import ArticleStage
from meca_engine.exceptions import ArticleLevelError
from meca_engine.logging_ import StructuredLogger, correlation_scope, trace_scope
from meca_engine.orchestrator.models import ArticleOutcome, OutcomeStatus, RunSummary
from meca_engine.orchestrator.queue_prep import already_complete, prepare_queue

if TYPE_CHECKING:
    from meca_engine.checkpoint.store import CheckpointStore
    from meca_engine.input.discovery import BatchDiscovery
    from meca_engine.input.models import ArticleReference, BatchSource
    from meca_engine.input.staging import Stager
    from meca_engine.orchestrator.scheduler import WorkerScheduler

_STAGE = "meca_engine.orchestrator.run_controller"


class RunController:
    """Coordinates one batch's discovery, resume-filtering, and staging.

    Attributes:
        discovery: Scans the batch source into article references.
        stager: Stages one article's files into a local working directory.
        checkpoint_store: Tracks per-article progress across runs.
        scheduler: Determines execution order/concurrency (sequential in
            Milestone 2).
        run_id: This run's unique identifier — used both as the staging
            workspace-scoping id and the structured-logging correlation id.
    """

    def __init__(
        self,
        discovery: BatchDiscovery,
        stager: Stager,
        checkpoint_store: CheckpointStore,
        scheduler: WorkerScheduler,
        logger: StructuredLogger,
        *,
        run_id: str | None = None,
    ) -> None:
        """Initialize the run controller.

        Args:
            discovery: The batch discovery scanner to use.
            stager: The stager to use for each article.
            checkpoint_store: The checkpoint store to consult and update.
            scheduler: The worker scheduler to execute staging tasks with.
            logger: The structured logger to emit run-level events through.
            run_id: A unique id for this run; auto-generated if omitted.
        """
        self._discovery = discovery
        self._stager = stager
        self._checkpoint_store = checkpoint_store
        self._scheduler = scheduler
        self._logger = logger
        self.run_id = run_id or uuid.uuid4().hex

    def run(self, source: BatchSource, *, batch_id: str) -> RunSummary:
        """Discover, resume-filter, and stage every article in a batch.

        Args:
            source: The batch source to process.
            batch_id: A human-readable identifier for this run's batch.

        Returns:
            A :class:`~meca_engine.orchestrator.models.RunSummary`
            covering every discovered article's outcome.

        Raises:
            BatchLevelError: Propagated unchanged if raised by discovery
                or staging — halts the run immediately, per
                12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §7.3.
        """
        started_at = datetime.now(timezone.utc)
        with correlation_scope(self.run_id):
            self._logger.audit(
                "Run starting",
                stage=_STAGE,
                context={"run_id": self.run_id, "batch_id": batch_id},
            )

            batch = self._discovery.discover(source, batch_id=batch_id)

            queue = prepare_queue(batch.article_refs, self._checkpoint_store)
            skipped_refs = already_complete(batch.article_refs, self._checkpoint_store)

            outcomes: list[ArticleOutcome] = [
                self._skipped_outcome(ref.article_id) for ref in skipped_refs
            ]
            for outcome in self._scheduler.schedule(queue, self._process_one):
                outcomes.append(outcome)
            for failure in batch.discovery_failures:
                outcomes.append(
                    ArticleOutcome(
                        article_id=failure.article_id or "<unknown>",
                        status=OutcomeStatus.FAILED,
                        stage_reached=ArticleStage.FAILED,
                        error_message=failure.reason,
                        exception_type=failure.exception_type,
                    )
                )

            completed_at = datetime.now(timezone.utc)
            summary = RunSummary(
                batch_id=batch_id,
                run_id=self.run_id,
                started_at=started_at,
                completed_at=completed_at,
                total_discovered=len(batch.article_refs) + len(batch.discovery_failures),
                total_discovery_failures=len(batch.discovery_failures),
                outcomes=tuple(outcomes),
            )
            self._logger.audit(
                "Run completed",
                stage=_STAGE,
                context={
                    "run_id": self.run_id,
                    "batch_id": batch_id,
                    "succeeded": summary.succeeded_count,
                    "failed": summary.failed_count,
                    "skipped": summary.skipped_count,
                },
            )
            return summary

    def _skipped_outcome(self, article_id: str) -> ArticleOutcome:
        record = self._checkpoint_store.get_record(article_id)
        stage = record.stage if record is not None else ArticleStage.STAGED
        self._logger.info(
            "Article already complete, skipping",
            stage=_STAGE,
            context={"article_id": article_id, "checkpoint_stage": stage.value},
        )
        return ArticleOutcome(
            article_id=article_id, status=OutcomeStatus.SKIPPED, stage_reached=stage
        )

    def _process_one(self, article_ref: ArticleReference) -> ArticleOutcome:
        article_id = article_ref.article_id
        with trace_scope(article_id):
            current_record = self._checkpoint_store.get_record(article_id)
            expected_current = current_record.stage if current_record is not None else None

            transitioned = self._checkpoint_store.transition(
                article_id,
                expected_current=expected_current,
                new_stage=ArticleStage.STAGING,
            )
            if not transitioned:
                self._logger.warn(
                    "Checkpoint transition collision; skipping this attempt",
                    stage=_STAGE,
                    context={"article_id": article_id},
                )
                return ArticleOutcome(
                    article_id=article_id,
                    status=OutcomeStatus.SKIPPED,
                    stage_reached=expected_current or ArticleStage.NOT_STARTED,
                    error_message="checkpoint transition collision",
                )

            try:
                staged_article = self._stager.stage_article(article_ref)
            except ArticleLevelError as exc:
                self._logger.log_exception(exc)
                self._checkpoint_store.transition(
                    article_id,
                    expected_current=ArticleStage.STAGING,
                    new_stage=ArticleStage.FAILED,
                    failure_reason=exc.message,
                )
                return ArticleOutcome(
                    article_id=article_id,
                    status=OutcomeStatus.FAILED,
                    stage_reached=ArticleStage.FAILED,
                    error_message=exc.message,
                    exception_type=type(exc).__name__,
                )

            self._checkpoint_store.transition(
                article_id,
                expected_current=ArticleStage.STAGING,
                new_stage=ArticleStage.STAGED,
            )
            return ArticleOutcome(
                article_id=article_id,
                status=OutcomeStatus.SUCCESS,
                stage_reached=ArticleStage.STAGED,
                staged_article=staged_article,
            )
