"""Console-only progress tracking for one :class:`ProcessingService` run.

No dashboard, no persistence — a future dashboard reads
:class:`ProgressSnapshot` instead (see :mod:`meca_engine.service.status`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ProgressSnapshot:
    """An immutable point-in-time view of one batch run's progress.

    Attributes:
        total: Total number of jobs in this run.
        completed: Number of jobs finished (succeeded, failed, or skipped).
        current_article_id: The article currently being processed, if any.
        started_at: When the run began.
        finished_at: When the run ended, if it has.
    """

    total: int
    completed: int
    current_article_id: str | None
    started_at: datetime
    finished_at: datetime | None

    @property
    def remaining(self) -> int:
        """Return how many jobs have not yet finished."""
        return self.total - self.completed

    @property
    def percentage(self) -> float:
        """Return completion percentage, rounded to 1 decimal place."""
        if self.total == 0:
            return 100.0
        return round(100 * self.completed / self.total, 1)

    @property
    def estimated_remaining_seconds(self) -> float | None:
        """Return a naive linear estimate of remaining time, or ``None`` if too early to tell."""
        if self.completed == 0:
            return None
        elapsed = (
            (self.finished_at or datetime.now(timezone.utc)) - self.started_at
        ).total_seconds()
        return round((elapsed / self.completed) * self.remaining, 1)


class ProgressTracker:
    """Tracks and prints a batch run's progress to the console."""

    def __init__(self, total: int) -> None:
        """Initialize a tracker for a run of ``total`` jobs."""
        self._total = total
        self._completed = 0
        self._current_article_id: str | None = None
        self._started_at = datetime.now(timezone.utc)
        self._finished_at: datetime | None = None

    def start_job(self, article_id: str) -> None:
        """Record that ``article_id`` has started processing, and print progress."""
        self._current_article_id = article_id
        print(f"[{self._completed + 1}/{self._total}] Processing {article_id}...")

    def complete_job(self) -> None:
        """Record that the current job has finished, and print progress."""
        self._completed += 1
        snapshot = self.snapshot()
        eta = snapshot.estimated_remaining_seconds
        eta_text = f", ~{eta:.0f}s remaining" if eta is not None else ""
        print(f"  -> {snapshot.completed}/{snapshot.total} ({snapshot.percentage}%){eta_text}")

    def finish(self) -> None:
        """Mark the run as finished."""
        self._finished_at = datetime.now(timezone.utc)

    def snapshot(self) -> ProgressSnapshot:
        """Return an immutable snapshot of the current progress."""
        return ProgressSnapshot(
            total=self._total,
            completed=self._completed,
            current_article_id=self._current_article_id,
            started_at=self._started_at,
            finished_at=self._finished_at,
        )
