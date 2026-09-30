"""Pluggable Checkpoint Store storage backends.

**As of Milestone 2**: :class:`~meca_engine.checkpoint.backends.in_memory.InMemoryCheckpointStore`
is implemented (suitable for local development, testing, and
single-process runs). A durable backend (Postgres/DynamoDB) is deferred
per 16_LLD_07_READINESS_ASSESSMENT.md §15.2 TQ-03.
"""

from __future__ import annotations

from meca_engine.checkpoint.backends.in_memory import InMemoryCheckpointStore

__all__ = ["InMemoryCheckpointStore"]
