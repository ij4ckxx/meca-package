"""Retry Manager — transient/permanent failure classification and exponential backoff (ADR-023).

Per 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.13. Classifies a caught
exception as retryable using the exception hierarchy's own, already-
established signal (:attr:`~meca_engine.exceptions.base.MecaEngineError.retryable`
— see :class:`~meca_engine.exceptions.article_errors.ArticleTransientError`
and its subclasses for the transient/infrastructure side of that split),
falling back to a conservative stdlib classification for exceptions the
engine has not yet wrapped (e.g. raw I/O errors surfaced directly by an
:class:`~meca_engine.providers.input.InputProvider`/
:class:`~meca_engine.providers.output.OutputProvider`).

Never classifies a deterministic, data-quality failure (a Business Rule
violation, a malformed-metadata error, an XML serialization error, a
missing source file) as retryable — those are :class:`MecaEngineError`
subclasses with ``retryable = False`` by class default, and the stdlib
fallback explicitly excludes the "file genuinely does not exist" family.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, TypeVar

from meca_engine.exceptions.base import MecaEngineError

if TYPE_CHECKING:
    from collections.abc import Callable

    from meca_engine.config.schema import RetrySettings
    from meca_engine.logging_.structured_logger import StructuredLogger

T = TypeVar("T")

# Raw (not-yet-wrapped) exceptions that generally indicate a transient
# infrastructure condition — temporary I/O contention, a file lock, a
# dropped connection, a momentarily unavailable service. Deliberately
# conservative: only conditions a retry can plausibly resolve.
_TRANSIENT_STDLIB_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ConnectionError,
    TimeoutError,
    BlockingIOError,
    InterruptedError,
    OSError,
)

# OSError subtypes that are deterministic, not transient — retrying them
# reproduces the identical failure. Checked before the broad OSError
# catch above.
_DETERMINISTIC_OS_ERRORS: tuple[type[BaseException], ...] = (
    FileNotFoundError,
    IsADirectoryError,
    NotADirectoryError,
)


def classify_retryable(exc: BaseException) -> bool:
    """Return whether ``exc`` represents a transient failure worth retrying.

    Args:
        exc: The caught exception.

    Returns:
        ``True`` only for infrastructure/operational failures (a
        :class:`MecaEngineError` explicitly marked ``retryable``, or an
        unwrapped transient stdlib I/O/network exception). Every
        deterministic conversion failure — Business Rule violations,
        Recovery Rule findings, missing source files, malformed
        metadata, XML errors, certification failures — returns ``False``.
    """
    if isinstance(exc, MecaEngineError):
        return exc.retryable
    if isinstance(exc, _DETERMINISTIC_OS_ERRORS):
        return False
    return isinstance(exc, _TRANSIENT_STDLIB_EXCEPTIONS)


def compute_backoff_seconds(attempt: int, settings: RetrySettings) -> float:
    """Return the exponential backoff delay before retry attempt ``attempt``.

    Args:
        attempt: The retry attempt number about to be made (1 for the
            first retry, following the initial attempt).
        settings: The configured backoff parameters.

    Returns:
        ``backoff_base_seconds * backoff_multiplier ** (attempt - 1)``,
        capped at ``backoff_max_seconds``.
    """
    delay = settings.backoff_base_seconds * (settings.backoff_multiplier ** (attempt - 1))
    return min(delay, settings.backoff_max_seconds)


def run_with_retry(  # noqa: UP047 (PEP 695 generics require Python 3.12; runtime targets 3.9)
    operation: Callable[[], T],
    *,
    settings: RetrySettings,
    logger: StructuredLogger | None = None,
    on_retry: Callable[[int, BaseException, float], None] | None = None,
) -> T:
    """Run ``operation``, retrying on transient failure with exponential backoff.

    Args:
        operation: The zero-argument callable to run.
        settings: Retry/backoff configuration (``max_attempts`` counts
            the initial attempt, so ``max_attempts=3`` means at most 2
            retries after the first failure).
        logger: If given, a warning is logged before each retry.
        on_retry: If given, called as ``on_retry(attempt, exc, delay)``
            immediately before sleeping for each retry — callers use
            this to track retry counts without this module needing to
            know about any caller-specific job/tracking model.

    Returns:
        Whatever ``operation()`` returns on its first successful attempt.

    Raises:
        BaseException: The last exception raised by ``operation``, once
            it is non-retryable or ``max_attempts`` is exhausted.
    """
    attempt = 1
    while True:
        try:
            return operation()
        except BaseException as exc:  # noqa: BLE001
            if not classify_retryable(exc) or attempt >= settings.max_attempts:
                raise
            delay = compute_backoff_seconds(attempt, settings)
            if logger is not None:
                logger.warn(
                    "Transient failure, retrying",
                    stage="meca_engine.retry",
                    context={
                        "attempt": str(attempt),
                        "max_attempts": str(settings.max_attempts),
                        "delay_seconds": str(delay),
                        "exception_type": type(exc).__name__,
                    },
                )
            if on_retry is not None:
                on_retry(attempt, exc, delay)
            time.sleep(delay)
            attempt += 1
