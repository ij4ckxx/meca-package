"""Targeted tests for the Milestone 13 reporting layer.

Lightweight by design (per the milestone's explicit testing scope): one
file covering all 7 new reporting modules with representative sample
data, not exhaustive per-branch coverage.
"""

from __future__ import annotations

import csv
import json

import pytest

from meca_engine.exceptions import FileReferenceMissingError
from meca_engine.model.warnings import (
    ConfidenceLevel,
    EngineWarning,
    FindingOrigin,
    WarningCategory,
    WarningSeverity,
)
from meca_engine.packaging.conversion_report import build_conversion_report
from meca_engine.packaging.models import PackageStatus, StagedPackage
from meca_engine.reporting import aggregation, analytics, csv_reports, dashboard, migration_summary
from meca_engine.reporting.certification_report import render_certification_report

pytestmark = pytest.mark.unit


def _recovery_warning(
    recovery_rule_id: str, confidence: ConfidenceLevel, affected_file: str | None
) -> EngineWarning:
    return EngineWarning(
        code="X",
        category=WarningCategory.SOURCE_DATA_INCONSISTENCY,
        severity=WarningSeverity.WARNING,
        origin=FindingOrigin.SOURCE_DATA_ISSUE,
        rule_id="BR-016",
        recovery_rule_id=recovery_rule_id,
        confidence=confidence,
        message=f"Recovered via {recovery_rule_id}.",
        article_id="a",
        suggested_action=None,
        is_recovery=True,
        affected_file=affected_file,
    )


@pytest.fixture
def sample_reports() -> list:
    clean = build_conversion_report(
        "cs-clean",
        staged_package=StagedPackage(
            article_id="cs-clean",
            zip_path=__import__("pathlib").Path("/tmp/MECA_cs-clean.zip"),
            doi="10.1042/cs-clean",
            packaged_files=(),
            xml_filenames=("cs-clean_article.xml",),
            status=PackageStatus.CERTIFIED,
        ),
        journal="Clinical Science",
    )

    recovered = build_conversion_report(
        "cs-recovered",
        staged_package=StagedPackage(
            article_id="cs-recovered",
            zip_path=__import__("pathlib").Path("/tmp/MECA_cs-recovered.zip"),
            doi="10.1042/cs-recovered",
            packaged_files=(),
            xml_filenames=("cs-recovered_article.xml",),
            status=PackageStatus.CERTIFIED_WITH_RECOVERY,
            warnings=(_recovery_warning("RR-004", ConfidenceLevel.LOW, "fig1.jpg"),),
        ),
        journal="Clinical Science",
    )

    partial = build_conversion_report(
        "bcj-partial",
        staged_package=StagedPackage(
            article_id="bcj-partial",
            zip_path=__import__("pathlib").Path("/tmp/MECA_bcj-partial.zip"),
            doi="10.1042/bcj-partial",
            packaged_files=(),
            xml_filenames=("bcj-partial_article.xml",),
            status=PackageStatus.PARTIAL_CERTIFICATION,
            warnings=(_recovery_warning("RR-002", ConfidenceLevel.MEDIUM, "license.pdf"),),
        ),
        journal="Biochemical Journal",
    )

    failed = build_conversion_report(
        "etls-failed",
        error=FileReferenceMissingError(
            "No manuscript file found", article_id="etls-failed", stage="x", rule_id="BR-011"
        ),
        failed_status=PackageStatus.FATAL_FAILURE,
        journal="Emerging Topics in Life Sciences",
    )

    return [clean, recovered, partial, failed]


# --- aggregation ---


def test_aggregate_counts_statuses_and_journals(sample_reports: list) -> None:
    stats = aggregation.aggregate(sample_reports)

    assert stats.total_articles == 4
    assert stats.status_counts["certified"] == 1
    assert stats.status_counts["partial_certification"] == 1
    assert stats.status_counts["fatal_failure"] == 1
    assert stats.journal_article_counts["Clinical Science"] == 2
    assert stats.recovery_rule_occurrences == {"RR-004": 1, "RR-002": 1}


def test_aggregate_business_rule_usage_marks_unreferenced_rules_unused(
    sample_reports: list,
) -> None:
    stats = aggregation.aggregate(sample_reports)

    assert stats.business_rule_usage["BR-016"].recovered == 2
    assert stats.business_rule_usage["BR-011"].fatal == 1
    assert stats.business_rule_usage["BR-001"].unused is True


# --- certification report ---


def test_certification_report_has_no_python_internals(sample_reports: list) -> None:
    html = render_certification_report(sample_reports[1])

    assert "cs-recovered" in html
    assert "Recovered via RR-004" in html
    assert "Traceback" not in html
    assert "object at 0x" not in html


def test_certification_report_flags_low_confidence_for_manual_review(sample_reports: list) -> None:
    html = render_certification_report(sample_reports[1])

    assert "Spot-check" in html


# --- migration summary ---


def test_migration_summary_renders_all_status_counts(sample_reports: list) -> None:
    html = migration_summary.render_migration_summary(sample_reports)

    assert "Migration Summary" in html
    assert "Total articles processed: <strong>4</strong>" in html
    assert "RR-004" in html


# --- csv reports ---


def test_archive_audit_csv_has_one_row_per_article(sample_reports: list, tmp_path) -> None:
    output_path = tmp_path / "Archive_Audit.csv"

    csv_reports.write_archive_audit_csv(sample_reports, output_path)

    with output_path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 4
    assert {row["Article ID"] for row in rows} == {r.article_id for r in sample_reports}


def test_manual_review_only_includes_articles_needing_attention(sample_reports: list) -> None:
    rows = csv_reports.build_manual_review_rows(sample_reports)

    articles = {row["Article"] for row in rows}
    assert "cs-clean" not in articles
    assert "bcj-partial" in articles
    assert "etls-failed" in articles
    assert rows[0]["Severity"] == "HIGH"


# --- analytics ---


def test_recovery_analytics_reports_most_common_and_journal_breakdown(sample_reports: list) -> None:
    text = analytics.render_recovery_analytics(sample_reports)

    assert "Most Common Recovery" in text
    assert "Clinical Science" in text


def test_business_rule_statistics_omits_unused_rules(sample_reports: list) -> None:
    text = analytics.render_business_rule_statistics(sample_reports)

    assert "BR-016" in text
    assert "BR-001 " not in text


# --- dashboard ---


def test_dashboard_json_is_serializable_and_has_one_entry_per_article(sample_reports: list) -> None:
    data = dashboard.build_dashboard_data(sample_reports)
    payload = json.dumps(data)

    parsed = json.loads(payload)
    assert len(parsed["articles"]) == 4
    assert parsed["summary"]["total_articles"] == 4


# --- package embed ---


def test_embed_conversion_report_adds_entry_to_zip(sample_reports: list, tmp_path) -> None:
    import zipfile

    from meca_engine.reporting.package_embed import embed_conversion_report

    zip_path = tmp_path / "MECA_cs-clean.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("cs-clean_article.xml", b"<article/>")

    embed_conversion_report(zip_path, sample_reports[0])

    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        assert "conversion-report.json" in names
        payload = json.loads(archive.read("conversion-report.json"))
        assert payload["article_id"] == "cs-clean"
