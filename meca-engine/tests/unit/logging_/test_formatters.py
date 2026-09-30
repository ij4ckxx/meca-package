"""Unit tests for meca_engine.logging_.formatters.StructuredJsonFormatter."""

from __future__ import annotations

import json
import logging

import pytest

from meca_engine.constants import (
    LOG_FIELD_CATEGORY,
    LOG_FIELD_CONTEXT,
    LOG_FIELD_CORRELATION_ID,
    LOG_FIELD_MESSAGE,
    LOG_FIELD_RULE_ID,
    LOG_FIELD_SEVERITY,
    LOG_FIELD_STAGE,
    LOG_FIELD_TIMESTAMP,
    LOG_FIELD_TRACE_ID,
)
from meca_engine.logging_.formatters import StructuredJsonFormatter
from meca_engine.logging_.record_fields import (
    EXTRA_CATEGORY,
    EXTRA_CONTEXT,
    EXTRA_CORRELATION_ID,
    EXTRA_RULE_ID,
    EXTRA_STAGE,
    EXTRA_TRACE_ID,
)

pytestmark = pytest.mark.unit


def _make_record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="meca_engine.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_format_emits_valid_json_with_all_schema_fields() -> None:
    formatter = StructuredJsonFormatter()
    record = _make_record(
        **{
            EXTRA_STAGE: "meca_engine.extraction.kriyadocs_parser",
            EXTRA_CATEGORY: "structured",
            EXTRA_RULE_ID: "BR-001",
            EXTRA_CONTEXT: {"key": "value"},
            EXTRA_CORRELATION_ID: "run-1",
            EXTRA_TRACE_ID: "cs-2025-8827",
        }
    )

    rendered = formatter.format(record)
    parsed = json.loads(rendered)

    assert parsed[LOG_FIELD_MESSAGE] == "hello world"
    assert parsed[LOG_FIELD_STAGE] == "meca_engine.extraction.kriyadocs_parser"
    assert parsed[LOG_FIELD_CATEGORY] == "structured"
    assert parsed[LOG_FIELD_SEVERITY] == "INFO"
    assert parsed[LOG_FIELD_RULE_ID] == "BR-001"
    assert parsed[LOG_FIELD_CONTEXT] == {"key": "value"}
    assert parsed[LOG_FIELD_CORRELATION_ID] == "run-1"
    assert parsed[LOG_FIELD_TRACE_ID] == "cs-2025-8827"
    assert LOG_FIELD_TIMESTAMP in parsed


def test_format_falls_back_gracefully_when_extra_fields_absent() -> None:
    formatter = StructuredJsonFormatter()
    record = _make_record()

    rendered = formatter.format(record)
    parsed = json.loads(rendered)

    assert parsed[LOG_FIELD_STAGE] == "meca_engine.test"
    assert parsed[LOG_FIELD_CATEGORY] == "structured"
    assert parsed[LOG_FIELD_RULE_ID] is None
    assert parsed[LOG_FIELD_CONTEXT] == {}
    assert parsed[LOG_FIELD_CORRELATION_ID] is None
    assert parsed[LOG_FIELD_TRACE_ID] is None


def test_format_includes_exception_when_present() -> None:
    formatter = StructuredJsonFormatter()
    try:
        raise ValueError("kaboom")
    except ValueError:
        import sys

        record = _make_record()
        record.exc_info = sys.exc_info()

    rendered = formatter.format(record)
    parsed = json.loads(rendered)

    assert "exception" in parsed
    assert "kaboom" in parsed["exception"]
