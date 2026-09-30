"""Performance-category timing helper.

Per 12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §6.3: "Performance events are
emitted at every stage boundary... feeding directly into the performance
benchmarks required by the Test Specification." :class:`PerformanceTimer`
is the one mechanism every pipeline stage uses to produce those events
consistently.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import TracebackType

    from meca_engine.logging_.structured_logger import StructuredLogger


class PerformanceTimer:
    """Context manager measuring a stage's wall-clock duration and logging it.

    Example:
        Used to time one pipeline stage and automatically emit a
        performance-category log event on exit, success or failure::

            with PerformanceTimer(logger, "extraction.parse", article_id="cs-2025-8827"):
                do_the_work()
    """

    def __init__(
        self,
        logger: StructuredLogger,
        stage: str,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        """Initialize a performance timer.

        Args:
            logger: The :class:`StructuredLogger` to emit the performance
                event through on exit.
            stage: Dotted package.module (and, conventionally, stage-name)
                path this timer measures.
            context: Additional structured context to attach to the emitted
                event (e.g. ``{"article_id": "..."}``).
        """
        self._logger = logger
        self._stage = stage
        self._context = dict(context) if context is not None else {}
        self._start_time: float = 0.0
        self.duration_ms: float | None = None
        """The measured duration, in milliseconds — ``None`` until the
        ``with`` block exits, then set regardless of whether it raised.
        Added in Milestone 6A so callers that need the value (not just
        the emitted log event) can read it back after the block."""

    def __enter__(self) -> PerformanceTimer:
        """Start the timer and return self."""
        self._start_time = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Stop the timer and emit a performance-category log event.

        Emits the event regardless of whether the timed block raised —
        the ``context`` carries a ``"succeeded"`` flag distinguishing the
        two cases, so failed stages are still measured (Test Specification
        §17-18 depend on this: a slow *failing* stage is just as important
        to observe as a slow successful one).
        """
        duration_ms = (time.perf_counter() - self._start_time) * 1000.0
        self.duration_ms = duration_ms
        context = {**self._context, "succeeded": exc_type is None}
        self._logger.performance(
            f"Stage '{self._stage}' completed in {duration_ms:.2f}ms",
            duration_ms=duration_ms,
            stage=self._stage,
            context=context,
        )
