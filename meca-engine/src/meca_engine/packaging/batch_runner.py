"""Batch execution for Package Assembly — Milestone 7.

Sequential only, matching :class:`meca_engine.orchestrator.scheduler.SequentialWorkerScheduler`'s
own "no parallel execution yet" precedent — the task instructions
explicitly forbid implementing distributed/parallel execution ahead of
its own approved milestone. Designed for that future extension without
requiring it now: each article is processed independently and
:class:`meca_engine.packaging.builder.PackageBuilder` is itself stateless
and reusable, so a future parallel scheduler can drive the same
per-article unit of work (:meth:`PackageBatchRunner._process_one`)
concurrently without any change to this class's core logic.

Resume semantics follow ADR-017 exactly (15_LLD_06 §14.4): an article
already at or past :attr:`ArticleStage.PACKAGED` is skipped entirely; an
article whose prior attempt did not reach ``PACKAGED`` (including one
stuck at the in-progress claim stage from a crashed run) is always
**redone from scratch** — never resumed mid-assembly — since
:class:`~meca_engine.packaging.builder.PackageBuilder` never leaves a
usable partial result to resume from.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING

from meca_engine.checkpoint.models import ArticleStage
from meca_engine.exceptions.base import MecaEngineError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from meca_engine.checkpoint.store import CheckpointStore
    from meca_engine.generators.context import GeneratorContext
    from meca_engine.logging_.structured_logger import StructuredLogger
    from meca_engine.packaging.builder import PackageBuilder
    from meca_engine.packaging.models import StagedPackage

_STAGE = "meca_engine.packaging.batch_runner"

# The in-progress "claim" stage this runner uses to reserve an article
# before attempting its (atomic) build — see module docstring.
_CLAIMED_STAGE = ArticleStage.GENERATED
_DONE_STAGE = ArticleStage.PACKAGED


@unique
class PackageOutcomeStatus(str, Enum):
    """The result of one article's package-assembly attempt in a batch."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class PackageOutcome:
    """One article's result within a :meth:`PackageBatchRunner.run` call.

    Attributes:
        exception: The original exception, present alongside
            ``error_message`` on a ``FAILED`` outcome. Added so a caller
            building a :class:`~meca_engine.packaging.conversion_report.ConversionReport`
            (which needs the real exception, not just its string form,
            to classify the failure) does not need to re-derive one from
            ``error_message``. Purely additive — every existing caller
            constructing a ``PackageOutcome`` without it is unaffected.
    """

    article_id: str
    status: PackageOutcomeStatus
    staged_package: StagedPackage | None = None
    error_message: str | None = None
    exception: MecaEngineError | None = None


class PackageBatchRunner:
    """Drives :class:`PackageBuilder` across many articles, with checkpoint-based resume."""

    def __init__(
        self,
        *,
        package_builder: PackageBuilder,
        checkpoint_store: CheckpointStore,
        logger: StructuredLogger,
    ) -> None:
        """Initialize the batch runner.

        Args:
            package_builder: The (stateless, reusable) orchestration point.
            checkpoint_store: Used to skip already-packaged articles and
                to claim/record each article's outcome.
            logger: Structured logger for batch-level events.
        """
        self._package_builder = package_builder
        self._checkpoint_store = checkpoint_store
        self._logger = logger

    def run(
        self, contexts: Sequence[GeneratorContext], *, output_root: Path
    ) -> tuple[PackageOutcome, ...]:
        """Assemble a package for every context, skipping already-completed articles.

        One article's failure never stops the batch — every remaining
        article is still attempted (mirroring
        :class:`meca_engine.exceptions.article_errors.ArticleLevelError`'s
        batch-continues-on-article-failure contract).

        Args:
            contexts: One :class:`~meca_engine.generators.context.GeneratorContext`
                per article to assemble.
            output_root: Passed through to every
                :meth:`~meca_engine.packaging.builder.PackageBuilder.build` call.

        Returns:
            One :class:`PackageOutcome` per input context, in the same order.
        """
        return tuple(self._process_one(context, output_root=output_root) for context in contexts)

    def _process_one(self, context: GeneratorContext, *, output_root: Path) -> PackageOutcome:
        article_id = context.model.identity.article_id
        record = self._checkpoint_store.get_record(article_id)
        current_stage = record.stage if record is not None else None

        if current_stage is not None and self._checkpoint_store.is_at_least(
            article_id, _DONE_STAGE
        ):
            self._logger.info(
                "package skipped: already complete",
                stage=_STAGE,
                context={"article_id": article_id, "stage": current_stage.value},
            )
            return PackageOutcome(article_id=article_id, status=PackageOutcomeStatus.SKIPPED)

        # ADR-017: any prior attempt short of PACKAGED (including a
        # crashed claim, or a previously FAILED attempt) is redone from
        # scratch, never resumed mid-way — claiming from whatever the
        # article's actual current stage is.
        if not self._checkpoint_store.transition(
            article_id, expected_current=current_stage, new_stage=_CLAIMED_STAGE
        ):
            self._logger.warn(
                "package skipped: another worker owns this article",
                stage=_STAGE,
                context={"article_id": article_id},
            )
            return PackageOutcome(article_id=article_id, status=PackageOutcomeStatus.SKIPPED)

        try:
            staged_package = self._package_builder.build(context, output_root=output_root)
        except MecaEngineError as exc:
            self._checkpoint_store.transition(
                article_id,
                expected_current=_CLAIMED_STAGE,
                new_stage=ArticleStage.FAILED,
                failure_reason=str(exc),
            )
            return PackageOutcome(
                article_id=article_id,
                status=PackageOutcomeStatus.FAILED,
                error_message=str(exc),
                exception=exc,
            )

        self._checkpoint_store.transition(
            article_id, expected_current=_CLAIMED_STAGE, new_stage=_DONE_STAGE
        )
        return PackageOutcome(
            article_id=article_id,
            status=PackageOutcomeStatus.SUCCEEDED,
            staged_package=staged_package,
        )
