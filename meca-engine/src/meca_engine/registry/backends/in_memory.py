"""In-memory DOI Registry backend.

Suitable for local development, testing, and single-process runs. Not
durable across process restarts — a real deployment needs a
database-backed implementation, deferred beyond Milestone 7, mirroring
:mod:`meca_engine.checkpoint.backends.in_memory`'s own deferral.
"""

from __future__ import annotations

import threading

from meca_engine.registry.doi_registry import DoiRegistry


class InMemoryDoiRegistry(DoiRegistry):
    """A thread-safe, process-local :class:`DoiRegistry` implementation.

    Backed by a plain ``dict`` (DOI -> reserving article_id) guarded by a
    lock, so the check-and-reserve in :meth:`reserve` is atomic with
    respect to other threads in the same process.
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory DOI registry."""
        self._reservations: dict[str, str] = {}
        self._lock = threading.Lock()

    def reserve(self, doi: str, *, article_id: str) -> bool:
        """Atomically reserve a DOI, unless a different article already holds it."""
        with self._lock:
            existing_article_id = self._reservations.get(doi)
            if existing_article_id is not None and existing_article_id != article_id:
                return False
            self._reservations[doi] = article_id
            return True

    def is_reserved(self, doi: str) -> bool:
        """Return whether a DOI has already been reserved by any article."""
        with self._lock:
            return doi in self._reservations

    def reset(self) -> None:
        """Clear every reservation. Test-only convenience, not part of the base interface."""
        with self._lock:
            self._reservations.clear()
