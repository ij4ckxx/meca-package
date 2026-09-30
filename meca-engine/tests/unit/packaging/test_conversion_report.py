"""Unit tests for meca_engine.packaging.conversion_report."""

from __future__ import annotations

from pathlib import Path

import pytest

from meca_engine.exceptions import FileReferenceMissingError
from meca_engine.generators.diagnostics import DiagnosticSeverity, GeneratorDiagnostic
from meca_engine.model.recovery_rules import SIGNIFICANT_DEFICIENCY_RULE_IDS
from meca_engine.model.warnings import (
    ConfidenceLevel,
    EngineWarning,
    FindingOrigin,
    WarningCategory,
    WarningSeverity,
)
from meca_engine.packaging.conversion_report import build_conversion_report
from meca_engine.packaging.models import PackageStatus, StagedPackage

pytestmark = pytest.mark.unit


def _status_for(warnings: tuple[EngineWarning, ...], diagnostics: tuple) -> PackageStatus:
    recoveries = [w for w in warnings if w.is_recovery]
    if any(w.recovery_rule_id in SIGNIFICANT_DEFICIENCY_RULE_IDS for w in recoveries):
        return PackageStatus.PARTIAL_CERTIFICATION
    if recoveries:
        return PackageStatus.CERTIFIED_WITH_RECOVERY
    if warnings or diagnostics:
        return PackageStatus.CERTIFIED_WITH_WARNINGS
    return PackageStatus.CERTIFIED


def _staged_package(
    warnings: tuple[EngineWarning, ...] = (), diagnostics: tuple = ()
) -> StagedPackage:
    return StagedPackage(
        article_id="cs-2025-0001",
        zip_path=Path("/tmp/MECA_cs-2025-0001.zip"),
        doi="10.1042/cs20250001",
        packaged_files=(),
        xml_filenames=("cs-2025-0001_article.xml",),
        status=_status_for(warnings, diagnostics),
        warnings=warnings,
        generator_diagnostics=diagnostics,
    )


def _warning(
    *,
    is_recovery: bool,
    rule_id: str | None = "BR-011",
    recovery_rule_id: str | None = "RR-004",
    affected_file: str | None = None,
) -> EngineWarning:
    return EngineWarning(
        code="BR011_FILE_ENTRY_SKIPPED",
        category=WarningCategory.SOURCE_DATA_INCONSISTENCY,
        severity=WarningSeverity.WARNING,
        origin=FindingOrigin.SOURCE_DATA_ISSUE,
        rule_id=rule_id,
        recovery_rule_id=recovery_rule_id if is_recovery else None,
        confidence=ConfidenceLevel.MEDIUM,
        message="Entry skipped.",
        article_id="cs-2025-0001",
        suggested_action=None,
        is_recovery=is_recovery,
        affected_file=affected_file,
    )


def test_clean_pass_has_full_confidence_and_no_findings() -> None:
    report = build_conversion_report("cs-2025-0001", staged_package=_staged_package())

    assert report.status is PackageStatus.CERTIFIED
    assert report.confidence_score == 100
    assert report.overall_confidence is ConfidenceLevel.HIGH
    assert report.warnings == ()
    assert report.recoveries == ()
    assert report.unrecoverable_error is None
    assert report.fatal_errors == ()
    assert report.business_rule_findings == ()
    assert report.recovery_rules_applied == ()
    assert report.missing_files == ()
    assert report.skipped_files == ()


def test_advisory_warning_is_separated_from_recovery() -> None:
    advisory = _warning(is_recovery=False)
    recovery = _warning(is_recovery=True, recovery_rule_id="RR-004")

    report = build_conversion_report(
        "cs-2025-0001", staged_package=_staged_package(warnings=(advisory, recovery))
    )

    assert report.warnings == (advisory,)
    assert report.recoveries == (recovery,)
    assert report.recovery_rules_applied == ("RR-004",)


def test_significant_deficiency_recovery_yields_partial_certification_and_missing_files() -> None:
    recovery = _warning(is_recovery=True, recovery_rule_id="RR-002", affected_file="license.pdf")

    report = build_conversion_report(
        "cs-2025-0001", staged_package=_staged_package(warnings=(recovery,))
    )

    assert report.status is PackageStatus.PARTIAL_CERTIFICATION
    assert report.missing_files == ("license.pdf",)
    assert report.skipped_files == ("license.pdf",)


def test_confidence_score_decreases_with_findings_and_floors_at_zero() -> None:
    many_warnings = tuple(_warning(is_recovery=False) for _ in range(50))

    report = build_conversion_report(
        "cs-2025-0001", staged_package=_staged_package(warnings=many_warnings)
    )

    assert report.confidence_score == 0
    assert report.overall_confidence is ConfidenceLevel.LOW


def test_generator_findings_are_carried_through() -> None:
    diagnostic = GeneratorDiagnostic(
        severity=DiagnosticSeverity.INFO, generator_name="reviews_xml", message="BR-103 gap"
    )

    report = build_conversion_report(
        "cs-2025-0001", staged_package=_staged_package(diagnostics=(diagnostic,))
    )

    assert report.generator_findings == (diagnostic,)
    assert report.status is PackageStatus.CERTIFIED_WITH_WARNINGS


def test_business_rule_findings_extracted_from_both_sources() -> None:
    warning = _warning(is_recovery=True, rule_id="BR-011")
    diagnostic = GeneratorDiagnostic(
        severity=DiagnosticSeverity.INFO,
        generator_name="reviews_xml",
        message="No overall_recommendation — BR-103's recommendation review-item is not emitted",
    )

    report = build_conversion_report(
        "cs-2025-0001",
        staged_package=_staged_package(warnings=(warning,), diagnostics=(diagnostic,)),
    )

    rule_ids = {f.rule_id for f in report.business_rule_findings}
    assert rule_ids == {"BR-011", "BR-103"}


def test_tracked_business_rules_split_into_passed_and_failed() -> None:
    warning = _warning(is_recovery=True, rule_id="BR-011")

    report = build_conversion_report(
        "cs-2025-0001", staged_package=_staged_package(warnings=(warning,))
    )

    assert "BR-011" in report.business_rules_failed
    assert "BR-011" not in report.business_rules_passed
    assert "BR-013" in report.business_rules_passed


def test_recovery_rule_id_extracted_from_generator_diagnostic_message() -> None:
    diagnostic = GeneratorDiagnostic(
        severity=DiagnosticSeverity.WARNING,
        generator_name="article_xml",
        message="license block omitted (recoverable, BR-063, RR-007)",
    )

    report = build_conversion_report(
        "cs-2025-0001", staged_package=_staged_package(diagnostics=(diagnostic,))
    )

    assert "RR-007" in report.recovery_rules_applied


def test_generated_files_come_from_packaged_files() -> None:
    from meca_engine.packaging.models import PackagedFile

    package = StagedPackage(
        article_id="cs-2025-0001",
        zip_path=Path("/tmp/MECA_cs-2025-0001.zip"),
        doi="10.1042/cs20250001",
        packaged_files=(
            PackagedFile(
                href="files/R1/fig1.jpg", source_path=Path("/x"), checksum="abc", size_bytes=1
            ),
        ),
        xml_filenames=("cs-2025-0001_article.xml",),
        status=PackageStatus.CERTIFIED,
    )

    report = build_conversion_report("cs-2025-0001", staged_package=package)

    assert report.generated_files == ("files/R1/fig1.jpg",)


def test_failed_conversion_has_zero_confidence_and_an_unrecoverable_error() -> None:
    error = FileReferenceMissingError(
        "No physical file found for 'manuscript.docx'",
        article_id="cs-2025-0001",
        stage="extraction.file_resolver",
        rule_id="BR-011",
    )

    report = build_conversion_report(
        "cs-2025-0001", error=error, failed_status=PackageStatus.FATAL_FAILURE
    )

    assert report.status is PackageStatus.FATAL_FAILURE
    assert report.confidence_score == 0
    assert report.overall_confidence is ConfidenceLevel.LOW
    assert report.unrecoverable_error is not None
    assert report.unrecoverable_error.error_type == "FileReferenceMissingError"
    assert report.unrecoverable_error.rule_id == "BR-011"
    assert report.fatal_errors == (report.unrecoverable_error,)
    assert report.business_rule_findings[0].rule_id == "BR-011"
    assert report.business_rules_failed == ("BR-011",)


def test_failed_conversion_defaults_to_fatal_failure() -> None:
    error = FileReferenceMissingError("boom", stage="x")

    report = build_conversion_report("cs-2025-0001", error=error)

    assert report.status is PackageStatus.FATAL_FAILURE
    assert report.fatal_errors == (report.unrecoverable_error,)


def test_engine_failure_status_is_honored() -> None:
    from meca_engine.exceptions import ModelBuildError

    error = ModelBuildError("invariant violated", stage="model.article")

    report = build_conversion_report(
        "cs-2025-0001", error=error, failed_status=PackageStatus.ENGINE_FAILURE
    )

    assert report.status is PackageStatus.ENGINE_FAILURE


def test_requires_either_staged_package_or_error() -> None:
    with pytest.raises(ValueError, match="requires either"):
        build_conversion_report("cs-2025-0001")


def test_to_dict_is_json_ready() -> None:
    import json

    warning = _warning(is_recovery=True, recovery_rule_id="RR-002", affected_file="license.pdf")
    report = build_conversion_report(
        "cs-2025-0001", staged_package=_staged_package(warnings=(warning,))
    )

    payload = json.dumps(report.to_dict())

    parsed = json.loads(payload)
    assert parsed["status"] == "partial_certification"
    assert parsed["confidence_score"] < 100
    assert parsed["recoveries"][0]["code"] == "BR011_FILE_ENTRY_SKIPPED"
    assert parsed["recoveries"][0]["recovery_rule_id"] == "RR-002"
    assert parsed["recoveries"][0]["recovery_applied"] is True
    assert parsed["recoveries"][0]["affected_file"] == "license.pdf"
    assert parsed["missing_files"] == ["license.pdf"]
    assert parsed["unrecoverable_error"] is None


def test_failed_report_to_dict_is_json_ready() -> None:
    import json

    error = FileReferenceMissingError(
        "boom", article_id="cs-2025-0001", stage="x", rule_id="BR-011"
    )
    report = build_conversion_report("cs-2025-0001", error=error)

    parsed = json.loads(json.dumps(report.to_dict()))

    assert parsed["unrecoverable_error"]["error_type"] == "FileReferenceMissingError"
    assert parsed["unrecoverable_error"]["rule_id"] == "BR-011"
    assert parsed["fatal_errors"][0]["error_type"] == "FileReferenceMissingError"


def test_generator_error_severity_carries_the_heaviest_confidence_penalty() -> None:
    info = GeneratorDiagnostic(severity=DiagnosticSeverity.INFO, generator_name="x", message="m")
    warning = GeneratorDiagnostic(
        severity=DiagnosticSeverity.WARNING, generator_name="x", message="m"
    )
    error = GeneratorDiagnostic(severity=DiagnosticSeverity.ERROR, generator_name="x", message="m")

    info_report = build_conversion_report("a", staged_package=_staged_package(diagnostics=(info,)))
    warning_report = build_conversion_report(
        "a", staged_package=_staged_package(diagnostics=(warning,))
    )
    error_report = build_conversion_report(
        "a", staged_package=_staged_package(diagnostics=(error,))
    )

    assert (
        info_report.confidence_score
        > warning_report.confidence_score
        > error_report.confidence_score
    )
