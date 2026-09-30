"""Generation Result — the return value of every generator's public entry point.

Milestone 6A (Generator Framework).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from meca_engine.generators.diagnostics import GeneratorDiagnostic

T = TypeVar("T")


@dataclass(frozen=True)
class GenerationResult(Generic[T]):  # noqa: UP046 — PEP 695 syntax needs Python 3.12 at runtime
    """The outcome of one successful :meth:`BaseGenerator.generate` call.

    Never constructed for a failed generation — a failure is always a
    raised :class:`~meca_engine.exceptions.GeneratorError` (or a
    lower-layer exception propagated unchanged), never a result object
    with a "failed" flag; this keeps error handling in one place (the
    exception hierarchy) rather than two.

    Attributes:
        document: The generator's specific output-document value.
        generator_name: Which generator produced this result.
        article_id: The article this result is for.
        duration_ms: Wall-clock generation time, in milliseconds.
        diagnostics: Every diagnostic recorded on the shared collector
            *up to and including* this generator's own run (a snapshot,
            not a live view — see
            :meth:`meca_engine.generators.diagnostics.DiagnosticsCollector.diagnostics`).
    """

    document: T
    generator_name: str
    article_id: str
    duration_ms: float
    diagnostics: tuple[GeneratorDiagnostic, ...]
