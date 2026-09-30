"""Unit tests for meca_engine.generators.diagnostics."""

from __future__ import annotations

import pytest

from meca_engine.generators.diagnostics import DiagnosticsCollector, DiagnosticSeverity

pytestmark = pytest.mark.unit


def test_new_collector_has_no_diagnostics() -> None:
    collector = DiagnosticsCollector()

    assert collector.diagnostics == ()
    assert collector.has_errors() is False


def test_info_records_an_info_severity_diagnostic() -> None:
    collector = DiagnosticsCollector()

    collector.info("raw_xml", "starting generation")

    assert len(collector.diagnostics) == 1
    entry = collector.diagnostics[0]
    assert entry.severity is DiagnosticSeverity.INFO
    assert entry.generator_name == "raw_xml"
    assert entry.message == "starting generation"
    assert entry.context == {}


def test_warn_records_a_warning_severity_diagnostic_with_context() -> None:
    collector = DiagnosticsCollector()

    collector.warn("manifest_xml", "unmapped category", context={"category": "tables"})

    entry = collector.diagnostics[0]
    assert entry.severity is DiagnosticSeverity.WARNING
    assert entry.context == {"category": "tables"}


def test_error_records_an_error_severity_diagnostic_without_raising() -> None:
    collector = DiagnosticsCollector()

    collector.error("reviews_xml", "inconsistent recommendation")

    assert collector.has_errors() is True
    assert collector.diagnostics[0].severity is DiagnosticSeverity.ERROR


def test_has_errors_false_when_only_info_and_warnings_recorded() -> None:
    collector = DiagnosticsCollector()

    collector.info("raw_xml", "note")
    collector.warn("raw_xml", "heads up")

    assert collector.has_errors() is False


def test_diagnostics_preserves_recorded_order_across_severities() -> None:
    collector = DiagnosticsCollector()

    collector.info("raw_xml", "first")
    collector.warn("article_xml", "second")
    collector.error("manifest_xml", "third")

    messages = [entry.message for entry in collector.diagnostics]
    assert messages == ["first", "second", "third"]


def test_diagnostics_property_returns_a_snapshot_not_a_live_view() -> None:
    collector = DiagnosticsCollector()
    collector.info("raw_xml", "first")

    snapshot = collector.diagnostics
    collector.info("raw_xml", "second")

    assert len(snapshot) == 1
    assert len(collector.diagnostics) == 2


def test_context_defaults_to_empty_mapping_when_omitted() -> None:
    collector = DiagnosticsCollector()

    collector.info("raw_xml", "note", context=None)

    assert collector.diagnostics[0].context == {}
