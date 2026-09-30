"""Pluggable DOI Registry storage backends (e.g. Postgres, DynamoDB).

**As of Milestone 7**: an in-memory backend
(:class:`~meca_engine.registry.backends.in_memory.InMemoryDoiRegistry`) is
implemented. A durable backend is deferred — see
16_LLD_07_READINESS_ASSESSMENT.md §15.2 TQ-03.
"""

from __future__ import annotations

from meca_engine.registry.backends.in_memory import InMemoryDoiRegistry

__all__ = [
    "InMemoryDoiRegistry",
]
