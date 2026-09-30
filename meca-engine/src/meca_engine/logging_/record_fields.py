"""Shared ``LogRecord.extra`` attribute names.

Internal to the :mod:`meca_engine.logging_` package — used by both
:mod:`~meca_engine.logging_.structured_logger` (to populate them) and
:mod:`~meca_engine.logging_.formatters` (to read them back), so the two
modules agree on the exact attribute name without either importing the
other's private state.
"""

from __future__ import annotations

from typing import Final

EXTRA_STAGE: Final[str] = "meca_stage"
EXTRA_CATEGORY: Final[str] = "meca_category"
EXTRA_RULE_ID: Final[str] = "meca_rule_id"
EXTRA_CONTEXT: Final[str] = "meca_context"
EXTRA_DURATION_MS: Final[str] = "meca_duration_ms"
EXTRA_CORRELATION_ID: Final[str] = "meca_correlation_id"
EXTRA_TRACE_ID: Final[str] = "meca_trace_id"
