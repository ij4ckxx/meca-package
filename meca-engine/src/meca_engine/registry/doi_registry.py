"""DOI Registry abstract interface — Package Assembly (Milestone 7).

Per 05_SYSTEM_MODULE_BREAKDOWN.md Module 7 ("DOI Registry Service") and
BR-154 (Business Rule Book §J): a DOI generated for one article must never
collide with a DOI already issued to another article in the same batch or
a prior run. This module validates uniqueness only — it never generates,
derives, or guesses a DOI value (that remains
:mod:`meca_engine.generators.article_xml.generator`'s responsibility per
BR-058/059, entirely outside this module's concern).

Modeled directly on :class:`meca_engine.checkpoint.store.CheckpointStore`:
an atomic check-and-reserve operation, so two concurrently-processed
articles can never both believe they hold the same DOI
(05_SYSTEM_MODULE_BREAKDOWN.md Module 7: "this is a shared-state
component, unlike the otherwise fully-parallel per-article pipeline").
Milestone 7 provides only the in-memory backend
(:mod:`meca_engine.registry.backends.in_memory`); a durable backend
(Postgres/DynamoDB) is deferred to the milestone that needs cross-run
durability in production, mirroring the Checkpoint Store's own deferral.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class DoiRegistry(ABC):
    """Durable (or, for Milestone 7, in-memory), atomic DOI uniqueness store.

    ``reserve`` is a compare-and-set: it succeeds if the DOI has never
    been reserved before, or if it was already reserved by the *same*
    ``article_id`` (idempotent re-reservation) — this is what lets a
    failed, redone-from-scratch package-assembly attempt (ADR-017; see
    :mod:`meca_engine.packaging.batch_runner`) re-run without a false
    collision against its own earlier, successful reservation, while
    still atomically preventing two *different* articles from ever both
    holding the same DOI.
    """

    @abstractmethod
    def reserve(self, doi: str, *, article_id: str) -> bool:
        """Atomically reserve a DOI, unless a different article already holds it.

        Args:
            doi: The already-generated DOI value to reserve (never
                generated or altered by this method).
            article_id: The article this DOI belongs to. Also part of the
                idempotency check: re-reserving a DOI already held by
                this same ``article_id`` succeeds (see class docstring).

        Returns:
            ``True`` if the DOI is now recorded as belonging to
            ``article_id`` — whether newly reserved or already held by
            this same article. ``False`` if the DOI was already reserved
            by a *different* article_id — callers must treat ``False``
            as a confirmed collision, per BR-154, and raise
            :class:`meca_engine.exceptions.article_errors.DoiCollisionError`
            rather than silently proceeding.
        """

    @abstractmethod
    def is_reserved(self, doi: str) -> bool:
        """Return whether a DOI has already been reserved by any article.

        Read-only check, e.g. for diagnostics or pre-flight reporting;
        never used in place of :meth:`reserve`'s atomic check-and-set for
        an actual reservation decision.
        """
