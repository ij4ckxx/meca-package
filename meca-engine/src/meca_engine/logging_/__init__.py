"""Logging Framework package (12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §6).

Named with a trailing underscore to avoid shadowing the stdlib ``logging``
module (10_LLD_01_STRUCTURE_AND_PACKAGES.md §2.1). Foundation-layer package —
depends only on :mod:`meca_engine.constants` and :mod:`meca_engine.exceptions`.
"""

from __future__ import annotations

from meca_engine.logging_.correlation import (
    correlation_scope,
    get_correlation_id,
    get_trace_id,
    reset_context,
    trace_scope,
)
from meca_engine.logging_.performance import PerformanceTimer
from meca_engine.logging_.structured_logger import (
    StructuredLogger,
    configure_root_logging,
    get_logger,
)

__all__ = [
    "PerformanceTimer",
    "StructuredLogger",
    "configure_root_logging",
    "correlation_scope",
    "get_correlation_id",
    "get_logger",
    "get_trace_id",
    "reset_context",
    "trace_scope",
]
