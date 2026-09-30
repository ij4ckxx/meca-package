"""DOI Registry Service — atomic check-and-reserve DOI uniqueness (ADR-015).

**As of Milestone 7**: the :class:`DoiRegistry` abstract interface and an
in-memory backend are implemented (BR-154 batch-wide uniqueness
validation for Package Assembly). A durable (database-backed) backend is
deferred — see `registry/backends/__init__.py` and
16_LLD_07_READINESS_ASSESSMENT.md §15.2 TQ-03.
"""

from __future__ import annotations

from meca_engine.registry.doi_registry import DoiRegistry

__all__ = [
    "DoiRegistry",
]
