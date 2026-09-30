"""Worker scheduling interface.

Per ADR-021: per-article parallelism is the intended long-term scaling
mechanism, but the current task explicitly requires "no parallel
execution yet; keep scheduling deterministic." This module defines the
:class:`WorkerScheduler` interface a future parallel implementation will
satisfy, plus the only concrete implementation built so far —
:class:`SequentialWorkerScheduler` — so
:class:`~meca_engine.orchestrator.run_controller.RunController` never
needs to change when real parallelism is introduced later.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

    from meca_engine.input.models import ArticleReference
    from meca_engine.orchestrator.models import ArticleOutcome


class WorkerScheduler(ABC):
    """Executes one task per queued item, yielding results as they complete."""

    @abstractmethod
    def schedule(
        self,
        tasks: Sequence[ArticleReference],
        task_fn: Callable[[ArticleReference], ArticleOutcome],
    ) -> Iterator[ArticleOutcome]:
        """Execute ``task_fn`` once per task and yield each result.

        Args:
            tasks: The queued article references to process, already
                deterministically ordered by the caller
                (:func:`~meca_engine.orchestrator.queue_prep.prepare_queue`).
            task_fn: The per-article processing function to invoke.

        Yields:
            One :class:`~meca_engine.orchestrator.models.ArticleOutcome`
            per task, in an order this scheduler defines (the sequential
            implementation preserves input order; a future parallel
            implementation may not).
        """


class SequentialWorkerScheduler(WorkerScheduler):
    """Processes tasks one at a time, in input order.

    The only concrete :class:`WorkerScheduler` implementation in
    Milestone 2, per the current task's explicit "no parallel execution
    yet" requirement.
    """

    def schedule(
        self,
        tasks: Sequence[ArticleReference],
        task_fn: Callable[[ArticleReference], ArticleOutcome],
    ) -> Iterator[ArticleOutcome]:
        """Execute ``task_fn`` for each task in order, yielding results as produced."""
        for task in tasks:
            yield task_fn(task)
