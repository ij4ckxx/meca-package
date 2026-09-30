"""Structured logging — the one API every module uses to emit log events.

Implements the five logging categories (structured, audit, performance,
error, debug) described in 12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §6.1-6.3
as convenience methods over a single underlying event schema, rather than
five separate logging subsystems.

Per 14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md §13.5: every module must log
through :func:`get_logger` / :class:`StructuredLogger` — never call
``logging.getLogger(...)`` or ``print`` directly outside this module.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

from meca_engine.constants import LogCategory
from meca_engine.logging_.correlation import get_correlation_id, get_trace_id
from meca_engine.logging_.formatters import StructuredJsonFormatter
from meca_engine.logging_.record_fields import (
    EXTRA_CATEGORY,
    EXTRA_CONTEXT,
    EXTRA_CORRELATION_ID,
    EXTRA_DURATION_MS,
    EXTRA_RULE_ID,
    EXTRA_STAGE,
    EXTRA_TRACE_ID,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from meca_engine.exceptions import MecaEngineError

_ROOT_LOGGER_NAME = "meca_engine"


def configure_root_logging(*, debug_enabled: bool = False, level: int = logging.INFO) -> None:
    """Configure the engine's root logger with the structured JSON formatter.

    Must be called exactly once, at application bootstrap
    (see :mod:`meca_engine.container`), before any :class:`StructuredLogger`
    emits its first event.

    Args:
        debug_enabled: Whether the DEBUG level (and therefore the debug
            logging category) is enabled. Never ``True`` in production
            (12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §6.3).
        level: The base logging level for non-debug output. Defaults to
            ``logging.INFO``.
    """
    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.setLevel(logging.DEBUG if debug_enabled else level)
    root.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    root.addHandler(handler)
    root.propagate = False


class StructuredLogger:
    """Structured, category-aware logger for one module/component.

    Every emitted event automatically carries the current
    :mod:`meca_engine.logging_.correlation` correlation id and trace id, so
    call sites never need to thread those ids through manually.

    Attributes:
        name: The dotted module path this logger represents, used as the
            default ``stage`` field value and as the underlying stdlib
            logger name.
        debug_enabled: Whether this logger's :meth:`debug` calls actually
            emit anything. Set once at construction from the resolved
            environment settings.
    """

    def __init__(self, name: str, *, debug_enabled: bool = False) -> None:
        """Initialize a structured logger.

        Args:
            name: The dotted module path this logger represents (e.g.
                ``"meca_engine.config.loader"``).
            debug_enabled: Whether debug-category events should be emitted.
        """
        self.name = name
        self.debug_enabled = debug_enabled
        self._logger = logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")

    def info(
        self,
        message: str,
        *,
        stage: str = "",
        rule_id: str | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        """Emit an INFO-severity, structured-category event."""
        self._emit(
            logging.INFO,
            message,
            category=LogCategory.STRUCTURED,
            stage=stage,
            rule_id=rule_id,
            context=context,
        )

    def warn(
        self,
        message: str,
        *,
        stage: str = "",
        rule_id: str | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        """Emit a WARN-severity, structured-category event."""
        self._emit(
            logging.WARNING,
            message,
            category=LogCategory.STRUCTURED,
            stage=stage,
            rule_id=rule_id,
            context=context,
        )

    def error(
        self,
        message: str,
        *,
        stage: str = "",
        rule_id: str | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        """Emit an ERROR-severity, error-category event."""
        self._emit(
            logging.ERROR,
            message,
            category=LogCategory.ERROR,
            stage=stage,
            rule_id=rule_id,
            context=context,
        )

    def critical(
        self,
        message: str,
        *,
        stage: str = "",
        rule_id: str | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        """Emit a CRITICAL-severity, error-category event."""
        self._emit(
            logging.CRITICAL,
            message,
            category=LogCategory.ERROR,
            stage=stage,
            rule_id=rule_id,
            context=context,
        )

    def audit(
        self,
        message: str,
        *,
        stage: str = "",
        context: Mapping[str, Any] | None = None,
    ) -> None:
        """Emit an audit-category event — an immutable record of a business decision.

        See 12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §6.3: audit events are
        additionally routed to an append-only store by the logging
        infrastructure's sink configuration (not implemented in Milestone 1;
        see 16_LLD_07_READINESS_ASSESSMENT.md deferred items).
        """
        self._emit(
            logging.INFO,
            message,
            category=LogCategory.AUDIT,
            stage=stage,
            context=context,
        )

    def performance(
        self,
        message: str,
        *,
        duration_ms: float,
        stage: str = "",
        context: Mapping[str, Any] | None = None,
    ) -> None:
        """Emit a performance-category event carrying a stage duration."""
        self._emit(
            logging.INFO,
            message,
            category=LogCategory.PERFORMANCE,
            stage=stage,
            context=context,
            duration_ms=duration_ms,
        )

    def debug(
        self,
        message: str,
        *,
        stage: str = "",
        context: Mapping[str, Any] | None = None,
    ) -> None:
        """Emit a debug-category event, only if debug logging is enabled.

        A no-op when :attr:`debug_enabled` is ``False`` — callers do not
        need to guard calls to this method themselves.
        """
        if not self.debug_enabled:
            return
        self._emit(
            logging.DEBUG,
            message,
            category=LogCategory.DEBUG,
            stage=stage,
            context=context,
        )

    def log_exception(self, error: MecaEngineError, *, message: str | None = None) -> None:
        """Log an already-classified :class:`MecaEngineError` as one error event.

        Per 14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md §13.5: every raised
        ``MecaEngineError`` subclass is logged exactly once, at the point
        it is caught and classified — never at the point it is raised, and
        never re-logged again as it propagates through further
        except/re-raise layers.

        Args:
            error: The caught, classified exception to log.
            message: Optional override for the log message; defaults to
                ``error.message``.
        """
        context = {
            "exception_type": type(error).__name__,
            "retryable": error.retryable,
            "inner_cause": repr(error.inner_cause) if error.inner_cause is not None else None,
        }
        self._emit(
            logging.ERROR,
            message or error.message,
            category=LogCategory.ERROR,
            stage=error.stage or self.name,
            rule_id=error.rule_id,
            context=context,
        )

    # --- internal ---

    def _emit(
        self,
        level: int,
        message: str,
        *,
        category: LogCategory,
        stage: str,
        rule_id: str | None = None,
        context: Mapping[str, Any] | None = None,
        duration_ms: float | None = None,
    ) -> None:
        extra = {
            EXTRA_STAGE: stage or self.name,
            EXTRA_CATEGORY: category.value,
            EXTRA_RULE_ID: rule_id,
            EXTRA_CONTEXT: dict(context) if context is not None else {},
            EXTRA_DURATION_MS: duration_ms,
            EXTRA_CORRELATION_ID: get_correlation_id(),
            EXTRA_TRACE_ID: get_trace_id(),
        }
        self._logger.log(level, message, extra=extra)


def get_logger(name: str, *, debug_enabled: bool = False) -> StructuredLogger:
    """Return a :class:`StructuredLogger` for the given module name.

    Args:
        name: The dotted module path the logger represents, conventionally
            ``__name__`` of the calling module.
        debug_enabled: Whether debug-category events should be emitted.

    Returns:
        A new :class:`StructuredLogger` instance bound to ``name``.
    """
    return StructuredLogger(name, debug_enabled=debug_enabled)
