"""Unit tests for meca_engine.reporting.certification_report."""

from __future__ import annotations

import pytest

from meca_engine.model.warnings import ConfidenceLevel
from meca_engine.packaging.conversion_report import ConversionReport, UnrecoverableError
from meca_engine.packaging.models import PackageStatus
from meca_engine.reporting.certification_report import render_certification_report

pytestmark = pytest.mark.unit


def test_failed_article_shows_the_specific_failure_reason() -> None:
    """Regression: the Certification Report must surface the real reason, not just a
    generic per-status sentence, for an engine_failure/fatal_failure article."""
    report = ConversionReport(
        article_id="ebc-2025-3025",
        status=PackageStatus.FATAL_FAILURE,
        confidence_score=0,
        overall_confidence=ConfidenceLevel.LOW,
        unrecoverable_error=UnrecoverableError(
            error_type="InvalidArticlePackageError",
            message="No source XML found for 'ebc-2025-3025' under /tmp/am_ebc-2025-3025_x",
            stage="meca_engine.providers.input",
            rule_id=None,
            article_id="ebc-2025-3025",
        ),
    )

    html = render_certification_report(report)

    assert "Failure Reason" in html
    assert "No source XML found for" in html
    assert "meca_engine.providers.input" in html


def test_successful_article_has_no_failure_reason_section() -> None:
    report = ConversionReport(
        article_id="cs-2025-0001",
        status=PackageStatus.CERTIFIED,
        confidence_score=100,
        overall_confidence=ConfidenceLevel.HIGH,
    )

    html = render_certification_report(report)

    assert "Failure Reason" not in html
