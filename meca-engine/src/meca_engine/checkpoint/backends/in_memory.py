"""In-memory Checkpoint Store backend.

Suitable for local development, testing, and single-process runs. Not
durable across process restarts — a real deployment needs a
database-backed implementation (16_LLD_07_READINESS_ASSESSMENT.md §15.2
TQ-03), deferred beyond Milestone 2.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from meca_engine.checkpoint.models import ArticleStage, CheckpointRecord
from meca_engine.checkpoint.store import CheckpointStore


class InMemoryCheckpointStore(CheckpointStore):
    """A thread-safe, process-local :class:`CheckpointStore` implementation.

    Backed by a plain ``dict`` guarded by a lock, so compare-and-set
    transitions are atomic with respect to other threads in the same
    process (sufficient for Milestone 2's deterministic, non-parallel
    scheduling; a future multi-process worker pool will need a durable,
    cross-process backend instead — see TQ-03).
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory checkpoint store."""
        self._records: dict[str, CheckpointRecord] = {}
        self._lock = threading.Lock()

    def get_record(self, article_id: str) -> CheckpointRecord | None:
        """Return the current checkpoint record for an article, if any."""
        with self._lock:
            return self._records.get(article_id)

    def transition(
        self,
        article_id: str,
        *,
        expected_current: ArticleStage | None,
        new_stage: ArticleStage,
        failure_reason: str | None = None,
    ) -> bool:
        """Atomically move an article to a new stage, if its current stage matches."""
        with self._lock:
            existing = self._records.get(article_id)
            actual_current = existing.stage if existing is not None else None
            if actual_current != expected_current:
                return False
            self._records[article_id] = CheckpointRecord(
                article_id=article_id,
                stage=new_stage,
                updated_at=datetime.now(timezone.utc),
                failure_reason=failure_reason,
            )
            return True

    def list_all(self) -> tuple[CheckpointRecord, ...]:
        """Return every checkpoint record currently known to the store."""
        with self._lock:
            return tuple(self._records.values())

    def reset(self) -> None:
        """Clear every record. Test-only convenience, not part of the base interface."""
        with self._lock:
            self._records.clear()
