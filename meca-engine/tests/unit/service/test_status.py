"""Unit tests for meca_engine.service.status."""

from __future__ import annotations

import pytest

from meca_engine.model.warnings import ConfidenceLevel
from meca_engine.packaging.conversion_report import ConversionReport
from meca_engine.packaging.models import PackageStatus
from meca_engine.service.job import Job, JobStatus
from meca_engine.service.status import build_status_view

pytestmark = pytest.mark.unit


def test_build_status_view_from_a_completed_report() -> None:
    job = Job(article_id="cs-2025-0001", journal="Clinical Science")
    job.status = JobStatus.SUCCEEDED
    job.output_location = "/out/cs-2025-0001"
    report = ConversionReport(
        article_id="cs-2025-0001",
        status=PackageStatus.CERTIFIED_WITH_RECOVERY,
        confidence_score=90,
        overall_confidence=ConfidenceLevel.HIGH,
    )

    view = build_status_view(job, report)

    assert view.article_id == "cs-2025-0001"
    assert view.job_status is JobStatus.SUCCEEDED
    assert view.conversion_status is PackageStatus.CERTIFIED_WITH_RECOVERY
    assert view.confidence_score == 90
    assert view.download_location == "/out/cs-2025-0001"


def test_build_status_view_for_a_skipped_job_has_no_report_fields() -> None:
    job = Job(article_id="cs-2025-0002")
    job.status = JobStatus.SKIPPED

    view = build_status_view(job, None)

    assert view.job_status is JobStatus.SKIPPED
    assert view.conversion_status is None
    assert view.confidence_score is None
    assert view.warnings == ()
    assert view.recoveries == ()
