"""Checkpoint Store — durable, atomic per-article processing state (ADR-022).

**As of Milestone 2**: the full :class:`ArticleStage` state machine, the
:class:`CheckpointStore` abstract interface, and an in-memory backend are
implemented. A durable (database-backed) backend is deferred — see
`checkpoint/backends/__init__.py` and 16_LLD_07_READINESS_ASSESSMENT.md
§15.2 TQ-03.
"""

from __future__ import annotations

from meca_engine.checkpoint.models import STAGE_ORDER, ArticleStage, CheckpointRecord, stage_index
from meca_engine.checkpoint.store import CheckpointStore

__all__ = [
    "STAGE_ORDER",
    "ArticleStage",
    "CheckpointRecord",
    "CheckpointStore",
    "stage_index",
]
