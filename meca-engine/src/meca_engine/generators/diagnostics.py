"""Generator diagnostics — non-fatal observations collected during generation.

Milestone 6A (Generator Framework). Mirrors the shape of
:mod:`meca_engine.extraction.parsed_model`'s ``ParseDiagnostic`` (severity
+ category-free message + context), deliberately re-implemented here
rather than imported: generators must not depend on the extraction layer
at all (per the Architecture Review's "no generator may access the parsed
XML or metadata directly" principle) — see the module docstring of
:mod:`meca_engine.generators.base` for the full dependency-direction
rationale.

A diagnostic is never raised as an exception — a genuinely fatal
condition uses the exception hierarchy instead
(:class:`meca_engine.exceptions.GeneratorInvariantError` and friends).
:class:`DiagnosticsCollector` is a plain, per-generation-run mutable
object (one instance per :class:`~meca_engine.generators.context.GeneratorContext`,
never shared across articles or across concurrent generations) — this is
the framework's one deliberately mutable object, matching item 12's
"avoid mutable *shared* state" (shared, not "avoid all mutability").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping


@unique
class DiagnosticSeverity(str, Enum):
    """Severity of one generator diagnostic."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class GeneratorDiagnostic:
    """One non-fatal observation made during XML generation.

    Attributes:
        severity: How serious this observation is.
        generator_name: The generator that emitted this diagnostic (e.g.
            ``"raw_xml"``) — always present, since a real run's
            diagnostics span every generator invoked for one article.
        message: A human-readable description.
        context: Additional structured detail, e.g. ``{"field": "..."}"``.
    """

    severity: DiagnosticSeverity
    generator_name: str
    message: str
    context: Mapping[str, Any] = field(default_factory=dict)


class DiagnosticsCollector:
    """Accumulates :class:`GeneratorDiagnostic` entries for one generation run.

    Never raises — recording a diagnostic never interrupts generation
    (item 10's explicit requirement). Read back via :attr:`diagnostics`
    (an immutable snapshot at call time) or :meth:`has_errors`.
    """

    def __init__(self) -> None:
        """Initialize an empty collector."""
        self._entries: list[GeneratorDiagnostic] = []

    def info(
        self, generator_name: str, message: str, *, context: Mapping[str, Any] | None = None
    ) -> None:
        """Record an informational observation."""
        self._add(DiagnosticSeverity.INFO, generator_name, message, context)

    def warn(
        self, generator_name: str, message: str, *, context: Mapping[str, Any] | None = None
    ) -> None:
        """Record a warning — a recoverable issue that generation proceeded past."""
        self._add(DiagnosticSeverity.WARNING, generator_name, message, context)

    def error(
        self, generator_name: str, message: str, *, context: Mapping[str, Any] | None = None
    ) -> None:
        """Record an error-severity observation that did not stop generation.

        For a condition that *must* stop generation, raise a
        :class:`~meca_engine.exceptions.GeneratorError` subclass instead
        of recording a diagnostic — this method is only for issues
        serious enough to flag strongly while generation still completes.
        """
        self._add(DiagnosticSeverity.ERROR, generator_name, message, context)

    @property
    def diagnostics(self) -> tuple[GeneratorDiagnostic, ...]:
        """Return every diagnostic recorded so far, in recorded order."""
        return tuple(self._entries)

    def has_errors(self) -> bool:
        """Return whether any ERROR-severity diagnostic was recorded."""
        return any(entry.severity is DiagnosticSeverity.ERROR for entry in self._entries)

    def _add(
        self,
        severity: DiagnosticSeverity,
        generator_name: str,
        message: str,
        context: Mapping[str, Any] | None,
    ) -> None:
        self._entries.append(
            GeneratorDiagnostic(
                severity=severity,
                generator_name=generator_name,
                message=message,
                context=dict(context) if context is not None else {},
            )
        )
