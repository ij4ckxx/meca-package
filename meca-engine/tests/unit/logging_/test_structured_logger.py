"""Unit tests for meca_engine.logging_.structured_logger.StructuredLogger."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from meca_engine.exceptions import FileReferenceMissingError
from meca_engine.logging_.correlation import correlation_scope, trace_scope
from meca_engine.logging_.record_fields import (
    EXTRA_CATEGORY,
    EXTRA_CONTEXT,
    EXTRA_CORRELATION_ID,
    EXTRA_DURATION_MS,
    EXTRA_RULE_ID,
    EXTRA_STAGE,
    EXTRA_TRACE_ID,
)
from meca_engine.logging_.structured_logger import StructuredLogger

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = pytest.mark.unit


class _ListHandler(logging.Handler):
    """A minimal handler that just remembers every record it receives."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def captured(request: pytest.FixtureRequest) -> Iterator[list[logging.LogRecord]]:
    """Attach a list-capturing handler directly to one uniquely-named child logger.

    Uses the requesting test's own node id as the logger name suffix so
    concurrent/parallel test runs never share logger state.
    """
    logger_name = f"meca_engine.test.{request.node.name}"
    underlying = logging.getLogger(logger_name)
    handler = _ListHandler()
    underlying.addHandler(handler)
    underlying.setLevel(logging.DEBUG)
    underlying.propagate = False
    try:
        yield handler.records
    finally:
        underlying.removeHandler(handler)


def _logger_for(request: pytest.FixtureRequest, *, debug_enabled: bool = False) -> StructuredLogger:
    return StructuredLogger(f"test.{request.node.name}", debug_enabled=debug_enabled)


def test_info_emits_structured_category_at_info_level(
    request: pytest.FixtureRequest, captured: list[logging.LogRecord]
) -> None:
    logger = _logger_for(request)

    logger.info("hello", stage="stage.x", rule_id="BR-001", context={"k": "v"})

    assert len(captured) == 1
    record = captured[0]
    assert record.levelno == logging.INFO
    assert getattr(record, EXTRA_CATEGORY) == "structured"
    assert getattr(record, EXTRA_STAGE) == "stage.x"
    assert getattr(record, EXTRA_RULE_ID) == "BR-001"
    assert getattr(record, EXTRA_CONTEXT) == {"k": "v"}


def test_warn_emits_at_warning_level(
    request: pytest.FixtureRequest, captured: list[logging.LogRecord]
) -> None:
    _logger_for(request).warn("careful")

    assert captured[0].levelno == logging.WARNING


def test_error_emits_error_category_at_error_level(
    request: pytest.FixtureRequest, captured: list[logging.LogRecord]
) -> None:
    _logger_for(request).error("failed")

    assert captured[0].levelno == logging.ERROR
    assert getattr(captured[0], EXTRA_CATEGORY) == "error"


def test_critical_emits_error_category_at_critical_level(
    request: pytest.FixtureRequest, captured: list[logging.LogRecord]
) -> None:
    _logger_for(request).critical("system down")

    assert captured[0].levelno == logging.CRITICAL
    assert getattr(captured[0], EXTRA_CATEGORY) == "error"


def test_audit_emits_audit_category(
    request: pytest.FixtureRequest, captured: list[logging.LogRecord]
) -> None:
    _logger_for(request).audit("DOI reserved", context={"doi": "10.1042/cs20258827"})

    assert getattr(captured[0], EXTRA_CATEGORY) == "audit"
    assert getattr(captured[0], EXTRA_CONTEXT) == {"doi": "10.1042/cs20258827"}


def test_performance_emits_performance_category_with_duration(
    request: pytest.FixtureRequest, captured: list[logging.LogRecord]
) -> None:
    _logger_for(request).performance("stage done", duration_ms=123.45)

    assert getattr(captured[0], EXTRA_CATEGORY) == "performance"
    assert getattr(captured[0], EXTRA_DURATION_MS) == 123.45


def test_debug_is_a_noop_when_disabled(
    request: pytest.FixtureRequest, captured: list[logging.LogRecord]
) -> None:
    _logger_for(request, debug_enabled=False).debug("verbose detail")

    assert captured == []


def test_debug_emits_when_enabled(
    request: pytest.FixtureRequest, captured: list[logging.LogRecord]
) -> None:
    _logger_for(request, debug_enabled=True).debug("verbose detail")

    assert len(captured) == 1
    assert getattr(captured[0], EXTRA_CATEGORY) == "debug"


def test_log_exception_captures_all_error_fields(
    request: pytest.FixtureRequest, captured: list[logging.LogRecord]
) -> None:
    error = FileReferenceMissingError(
        "manuscript.docx not found",
        article_id="cs-2025-8827",
        stage="meca_engine.extraction.file_resolver",
        rule_id="BR-011",
    )

    _logger_for(request).log_exception(error)

    record = captured[0]
    assert record.levelno == logging.ERROR
    assert getattr(record, EXTRA_STAGE) == "meca_engine.extraction.file_resolver"
    assert getattr(record, EXTRA_RULE_ID) == "BR-011"
    context = getattr(record, EXTRA_CONTEXT)
    assert context["exception_type"] == "FileReferenceMissingError"
    assert context["retryable"] is False


def test_correlation_and_trace_ids_are_attached_automatically(
    request: pytest.FixtureRequest, captured: list[logging.LogRecord]
) -> None:
    logger = _logger_for(request)

    with correlation_scope("run-1"), trace_scope("cs-2025-8827"):
        logger.info("inside scope")

    record = captured[0]
    assert getattr(record, EXTRA_CORRELATION_ID) == "run-1"
    assert getattr(record, EXTRA_TRACE_ID) == "cs-2025-8827"


def test_stage_defaults_to_logger_name_when_not_supplied(
    request: pytest.FixtureRequest, captured: list[logging.LogRecord]
) -> None:
    logger = _logger_for(request)

    logger.info("no explicit stage")

    assert getattr(captured[0], EXTRA_STAGE) == logger.name
