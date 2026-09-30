"""Deterministic queue preparation and resume filtering.

Per ADR-022: an article already at or past the "staged" checkpoint stage
on a resumed run must be skipped, not reprocessed. Per the current task's
"keep scheduling deterministic" requirement: the resulting queue is
always sorted by ``article_id`` so re-running the same batch twice visits
articles in the same order.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.checkpoint.models import ArticleStage

if TYPE_CHECKING:
    from meca_engine.checkpoint.store import CheckpointStore
    from meca_engine.input.models import ArticleReference


def prepare_queue(
    article_refs: tuple[ArticleReference, ...],
    checkpoint_store: CheckpointStore,
    *,
    minimum_complete_stage: ArticleStage = ArticleStage.STAGED,
) -> tuple[ArticleReference, ...]:
    """Sort article references deterministically and filter out already-complete ones.

    Args:
        article_refs: The article references to prepare a queue from.
        checkpoint_store: Consulted to determine which articles are
            already at or past ``minimum_complete_stage``.
        minimum_complete_stage: The stage at or beyond which an article
            is considered already done and is skipped.

    Returns:
        The article references that still need processing, sorted by
        ``article_id`` ascending.
    """
    sorted_refs = tuple(sorted(article_refs, key=lambda ref: ref.article_id))
    return tuple(
        ref
        for ref in sorted_refs
        if not checkpoint_store.is_at_least(ref.article_id, minimum_complete_stage)
    )


def already_complete(
    article_refs: tuple[ArticleReference, ...],
    checkpoint_store: CheckpointStore,
    *,
    minimum_complete_stage: ArticleStage = ArticleStage.STAGED,
) -> tuple[ArticleReference, ...]:
    """Return the subset of ``article_refs`` already at or past ``minimum_complete_stage``.

    The complement of :func:`prepare_queue`, used by
    :class:`~meca_engine.orchestrator.run_controller.RunController` to
    report ``SKIPPED`` outcomes for articles this run did not touch.

    Args:
        article_refs: The article references to check.
        checkpoint_store: Consulted for each article's current stage.
        minimum_complete_stage: The stage at or beyond which an article
            counts as already complete.

    Returns:
        The article references already at or past ``minimum_complete_stage``,
        sorted by ``article_id`` ascending.
    """
    sorted_refs = tuple(sorted(article_refs, key=lambda ref: ref.article_id))
    return tuple(
        ref
        for ref in sorted_refs
        if checkpoint_store.is_at_least(ref.article_id, minimum_complete_stage)
    )
