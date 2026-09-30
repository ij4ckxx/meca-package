"""Job model — one article's unit of work within the Processing Service."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from datetime import datetime


@unique
class JobStatus(str, Enum):
    """A job's position in its own lifecycle."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


def _new_job_id() -> str:
    return uuid4().hex


@dataclass
class Job:
    """One article's conversion request as it moves through the service.

    Mutable by design: a :class:`~meca_engine.service.worker.Worker` updates
    ``status``/``started_at``/``finished_at``/``retry_count`` in place as it
    processes the job, and fills in ``journal``/``input_location``/
    ``output_location`` once each becomes known (``journal`` is only
    discoverable after metadata extraction; ``input_location``/
    ``output_location`` only once the configured providers resolve them).

    Attributes:
        article_id: The article this job converts.
        job_id: A unique identifier for this job (distinct from
            ``article_id`` — a future retry-as-new-job policy could reuse
            the same ``article_id`` under a new ``job_id``).
        journal: The article's journal display name, once known.
        input_location: Where this job's source was staged from.
        output_location: Where this job's output package was written.
        status: This job's current lifecycle state.
        started_at: When processing began.
        finished_at: When processing ended (success, failure, or skip).
        retry_count: How many transient-failure retries this job has
            gone through so far.
    """

    article_id: str
    job_id: str = field(default_factory=_new_job_id)
    journal: str = ""
    input_location: str = ""
    output_location: str = ""
    status: JobStatus = JobStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    retry_count: int = 0

    @property
    def duration_seconds(self) -> float | None:
        """Return elapsed processing time, or ``None`` if not yet finished."""
        if self.started_at is None or self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()
