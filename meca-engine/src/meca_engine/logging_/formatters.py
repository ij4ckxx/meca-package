"""JSON structured-log formatter.

Renders one JSON object per log line, matching the structured log event
schema in 12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §6.2 exactly.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from meca_engine.constants import (
    LOG_FIELD_CATEGORY,
    LOG_FIELD_CONTEXT,
    LOG_FIELD_CORRELATION_ID,
    LOG_FIELD_DURATION_MS,
    LOG_FIELD_MESSAGE,
    LOG_FIELD_RULE_ID,
    LOG_FIELD_SEVERITY,
    LOG_FIELD_STAGE,
    LOG_FIELD_TIMESTAMP,
    LOG_FIELD_TRACE_ID,
    LOG_TIMESTAMP_FORMAT,
)
from meca_engine.logging_.record_fields import (
    EXTRA_CATEGORY,
    EXTRA_CONTEXT,
    EXTRA_CORRELATION_ID,
    EXTRA_DURATION_MS,
    EXTRA_RULE_ID,
    EXTRA_STAGE,
    EXTRA_TRACE_ID,
)


class StructuredJsonFormatter(logging.Formatter):
    """Formats every :class:`logging.LogRecord` as one structured JSON line.

    Reads the structured fields (stage, category, rule_id, context,
    duration_ms, correlation_id, trace_id) from the record's ``extra``
    attributes, which :class:`~meca_engine.logging_.structured_logger.StructuredLogger`
    always populates — this formatter never needs to know about
    :mod:`meca_engine.logging_.correlation` directly, since the logger
    already resolved those ids before emitting the record.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Render one log record as a single-line JSON string.

        Args:
            record: The stdlib log record to format.

        Returns:
            A JSON-encoded string representing the structured log event.
        """
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            LOG_TIMESTAMP_FORMAT
        )
        event: dict[str, Any] = {
            LOG_FIELD_TIMESTAMP: timestamp,
            LOG_FIELD_CORRELATION_ID: getattr(record, EXTRA_CORRELATION_ID, None),
            LOG_FIELD_TRACE_ID: getattr(record, EXTRA_TRACE_ID, None),
            LOG_FIELD_STAGE: getattr(record, EXTRA_STAGE, record.name),
            LOG_FIELD_CATEGORY: getattr(record, EXTRA_CATEGORY, "structured"),
            LOG_FIELD_SEVERITY: record.levelname,
            LOG_FIELD_RULE_ID: getattr(record, EXTRA_RULE_ID, None),
            LOG_FIELD_MESSAGE: record.getMessage(),
            LOG_FIELD_CONTEXT: getattr(record, EXTRA_CONTEXT, None) or {},
            LOG_FIELD_DURATION_MS: getattr(record, EXTRA_DURATION_MS, None),
        }
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, default=str, sort_keys=False)
