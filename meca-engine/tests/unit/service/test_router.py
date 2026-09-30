"""Unit tests for meca_engine.service.router."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from meca_engine.packaging.conversion_report import ConversionReport
from meca_engine.packaging.models import PackageStatus
from meca_engine.providers.output import LocalOutputProvider
from meca_engine.service.router import (
    FAILED,
    MANUAL_REVIEW,
    UPLOADED,
    OutputRouter,
    decide_category,
)

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (PackageStatus.CERTIFIED, UPLOADED),
        (PackageStatus.CERTIFIED_WITH_WARNINGS, UPLOADED),
        (PackageStatus.CERTIFIED_WITH_RECOVERY, UPLOADED),
        (PackageStatus.PARTIAL_CERTIFICATION, MANUAL_REVIEW),
        (PackageStatus.ENGINE_FAILURE, FAILED),
        (PackageStatus.FATAL_FAILURE, FAILED),
    ],
)
def test_decide_category(status: PackageStatus, expected: str) -> None:
    assert decide_category(status) == expected


def test_route_built_package_moves_directory_to_uploaded(tmp_path: Path) -> None:
    provider = LocalOutputProvider(str(tmp_path))
    staged_root = provider.article_output_root("cs-2025-0001")
    (staged_root / "MECA_cs-2025-0001.zip").write_bytes(b"zip bytes")
    report = ConversionReport(
        article_id="cs-2025-0001", status=PackageStatus.CERTIFIED, confidence_score=100
    )
    router = OutputRouter(provider)

    destination = router.route_built_package("cs-2025-0001", staged_root, report)

    assert destination == tmp_path / "uploaded" / "cs-2025-0001"
    assert (destination / "MECA_cs-2025-0001.zip").is_file()
    assert not staged_root.exists()
    assert not (destination / "conversion-report.json").exists()


def test_route_built_package_to_manual_review_also_writes_conversion_report_json(
    tmp_path: Path,
) -> None:
    provider = LocalOutputProvider(str(tmp_path))
    staged_root = provider.article_output_root("cs-2025-0002")
    (staged_root / "MECA_cs-2025-0002.zip").write_bytes(b"zip bytes")
    report = ConversionReport(
        article_id="cs-2025-0002",
        status=PackageStatus.PARTIAL_CERTIFICATION,
        confidence_score=40,
    )
    router = OutputRouter(provider)

    destination = router.route_built_package("cs-2025-0002", staged_root, report)

    assert destination == tmp_path / "manual_review" / "cs-2025-0002"
    report_path = destination / "conversion-report.json"
    assert report_path.is_file()
    assert json.loads(report_path.read_text())["article_id"] == "cs-2025-0002"


def test_route_failed_article_writes_certification_report_and_json(tmp_path: Path) -> None:
    provider = LocalOutputProvider(str(tmp_path))
    report = ConversionReport(
        article_id="cs-2025-0003", status=PackageStatus.ENGINE_FAILURE, confidence_score=0
    )
    router = OutputRouter(provider)

    destination = router.route_failed_article(report)

    assert destination == tmp_path / "failed" / "cs-2025-0003"
    assert (destination / "MECA_cs-2025-0003_Certification_Report.html").is_file()
    assert (destination / "conversion-report.json").is_file()
