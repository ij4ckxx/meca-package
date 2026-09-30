"""Orchestrator / Run Controller.

Top-level batch coordination. The only package permitted to import every
other package (10_LLD_01_STRUCTURE_AND_PACKAGES.md §2.3).

**As of Milestone 2**: batch lifecycle (discovery → resume-filter →
staging), a deterministic sequential :class:`WorkerScheduler`, and
checkpoint-based resume support are implemented. Real parallel execution,
and every stage from metadata-loading onward, remain deferred to later
milestones (`08_IMPLEMENTATION_ROADMAP.md` Phases 2-6).
"""

from __future__ import annotations

from meca_engine.orchestrator.models import ArticleOutcome, OutcomeStatus, RunSummary
from meca_engine.orchestrator.queue_prep import already_complete, prepare_queue
from meca_engine.orchestrator.run_controller import RunController
from meca_engine.orchestrator.scheduler import SequentialWorkerScheduler, WorkerScheduler

__all__ = [
    "ArticleOutcome",
    "OutcomeStatus",
    "RunController",
    "RunSummary",
    "SequentialWorkerScheduler",
    "WorkerScheduler",
    "already_complete",
    "prepare_queue",
]
