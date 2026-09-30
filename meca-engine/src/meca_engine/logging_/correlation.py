"""Correlation-id and per-article trace-id propagation.

Per 12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §6.4:

- ``correlation_id`` identifies one batch **run**.
- ``trace_id`` identifies one **article** (set to the article's own
  ``article_id`` — no separate UUID is manufactured).

Both are carried via :class:`contextvars.ContextVar` so that every logging
call site can read them automatically without threading them through every
function signature by hand, safely across ``asyncio``/thread boundaries
within one process. Across process boundaries (multiprocessing workers,
per ADR-021), the ids must be passed explicitly into the worker task and
re-established via :func:`correlation_scope` / :func:`trace_scope` at the
start of that task — context variables do not cross a process boundary on
their own.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


def get_correlation_id() -> str | None:
    """Return the current run's correlation id, or ``None`` if unset."""
    return _correlation_id_var.get()


def get_trace_id() -> str | None:
    """Return the current article's trace id, or ``None`` if unset."""
    return _trace_id_var.get()


@contextmanager
def correlation_scope(correlation_id: str) -> Iterator[None]:
    """Scope a block of code to a given batch-run correlation id.

    Args:
        correlation_id: The correlation id to set for the duration of the
            ``with`` block. Restored to its previous value on exit.

    Yields:
        None.
    """
    token = _correlation_id_var.set(correlation_id)
    try:
        yield
    finally:
        _correlation_id_var.reset(token)


@contextmanager
def trace_scope(trace_id: str) -> Iterator[None]:
    """Scope a block of code to a given article trace id.

    Args:
        trace_id: The trace id (conventionally the article's own
            ``article_id``) to set for the duration of the ``with`` block.
            Restored to its previous value on exit.

    Yields:
        None.
    """
    token = _trace_id_var.set(trace_id)
    try:
        yield
    finally:
        _trace_id_var.reset(token)


def reset_context() -> None:
    """Clear both the correlation id and trace id back to unset.

    Intended for test suites to call between tests (see ``tests/conftest.py``)
    so that a test which sets an id via :func:`correlation_scope` /
    :func:`trace_scope` and fails before the context manager exits can never
    leak that id into a later, unrelated test. Not used by production code
    paths, which always rely on the scoped context managers instead.
    """
    _correlation_id_var.set(None)
    _trace_id_var.set(None)
