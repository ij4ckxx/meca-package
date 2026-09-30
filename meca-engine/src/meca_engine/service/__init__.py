"""Processing Service — the permanent orchestration layer for the conversion engine.

Replaces the batch script's inline orchestration with a reusable
:class:`~meca_engine.service.processing_service.ProcessingService`, built via
:func:`~meca_engine.service.service_factory.build_processing_service`. Every
conversion step (extraction, transformation, generation, packaging,
certification, reporting, intelligence) is reused unchanged; this package
only owns job creation, sequential dispatch, progress tracking, and
operational retry.
"""

from __future__ import annotations

from meca_engine.service.job import Job, JobStatus
from meca_engine.service.processing_service import ProcessingService
from meca_engine.service.progress import ProgressSnapshot, ProgressTracker
from meca_engine.service.queue import JobQueue
from meca_engine.service.router import OutputRouter, decide_category
from meca_engine.service.service_factory import build_processing_service
from meca_engine.service.status import BatchStatusSnapshot, PackageStatusView, build_status_view
from meca_engine.service.worker import Worker

__all__ = [
    "BatchStatusSnapshot",
    "Job",
    "JobQueue",
    "JobStatus",
    "OutputRouter",
    "PackageStatusView",
    "ProcessingService",
    "ProgressSnapshot",
    "ProgressTracker",
    "Worker",
    "build_processing_service",
    "build_status_view",
    "decide_category",
]
