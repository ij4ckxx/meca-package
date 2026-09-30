"""Targeted tests for the Milestone 14 Migration Intelligence Layer.

Lightweight by design (per the milestone's explicit testing scope): one
file, representative fixtures per rule/statistic, not exhaustive
per-branch coverage. No engine code is exercised — every fixture builds
a :class:`ConversionReport` directly.
"""

from __future__ import annotations

import json
from pathlib import Path

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
from meca_engine.reporting.intelligence import (
    business_rule_statistics,
    confidence_statistics,
    corpus_analyzer,
    journal_statistics,
    recommendation_engine,
    recovery_statistics,
    trend_analyzer,
    warning_statistics,
)

pytestmark = pytest.mark.unit


def _warning(
    *, rule_id: str, recovery_rule_id: str | None, confidence: ConfidenceLevel, is_recovery: bool
) -> EngineWarning:
    return EngineWarning(
        code=f"CODE_{rule_id}",
        category=WarningCategory.SOURCE_DATA_INCONSISTENCY,
        severity=WarningSeverity.WARNING,
        origin=FindingOrigin.SOURCE_DATA_ISSUE,
        rule_id=rule_id,
        recovery_rule_id=recovery_rule_id,
        confidence=confidence,
        message=f"Finding for {rule_id}.",
        article_id="a",
        suggested_action=None,
        is_recovery=is_recovery,
    )


def _report(
    article_id: str,
    journal: str,
    *,
    status: PackageStatus = PackageStatus.CERTIFIED,
    warnings: tuple[EngineWarning, ...] = (),
):
    return build_conversion_report(
        article_id,
        staged_package=StagedPackage(
            article_id=article_id,
            zip_path=Path(f"/tmp/MECA_{article_id}.zip"),
            doi=f"10.1042/{article_id}",
            packaged_files=(),
            xml_filenames=(f"{article_id}_article.xml",),
            status=status,
            warnings=warnings,
        ),
        journal=journal,
    )


@pytest.fixture
def mixed_reports() -> list:
    clean = _report("clean-1", "Journal A")
    recovered = _report(
        "recovered-1",
        "Journal A",
        status=PackageStatus.CERTIFIED_WITH_RECOVERY,
        warnings=(
            _warning(
                rule_id="BR-016",
                recovery_rule_id="RR-004",
                confidence=ConfidenceLevel.LOW,
                is_recovery=True,
            ),
        ),
    )
    partial = _report(
        "partial-1",
        "Journal B",
        status=PackageStatus.PARTIAL_CERTIFICATION,
        warnings=(
            _warning(
                rule_id="BR-011",
                recovery_rule_id="RR-002",
                confidence=ConfidenceLevel.MEDIUM,
                is_recovery=True,
            ),
        ),
    )
    failed = build_conversion_report(
        "failed-1",
        error=FileReferenceMissingError(
            "no manuscript", article_id="failed-1", stage="x", rule_id="BR-011"
        ),
        failed_status=PackageStatus.FATAL_FAILURE,
        journal="Journal B",
    )
    return [clean, recovered, partial, failed]


# --- corpus_analyzer ---


def test_build_corpus_normalizes_fields(mixed_reports: list) -> None:
    records = corpus_analyzer.build_corpus(mixed_reports)

    by_id = {r.article_id: r for r in records}
    assert by_id["recovered-1"].business_rules_recovered == ("BR-016",)
    assert by_id["partial-1"].recovery_rules_triggered == ("RR-002",)
    assert by_id["failed-1"].succeeded is False
    assert by_id["clean-1"].succeeded is True


def test_migration_intelligence_report_and_dashboard_are_generated(mixed_reports: list) -> None:
    html = corpus_analyzer.render_migration_intelligence_report(mixed_reports)
    dashboard = corpus_analyzer.build_dashboard_intelligence(mixed_reports)

    assert "Migration Intelligence Report" in html
    assert dashboard["total_articles"] == 4
    json.dumps(dashboard)  # must be fully JSON-serializable


# --- journal_statistics ---


def test_journal_statistics_group_correctly(mixed_reports: list) -> None:
    records = corpus_analyzer.build_corpus(mixed_reports)
    stats = journal_statistics.compute_journal_statistics(records)

    assert stats["Journal A"].article_count == 2
    assert stats["Journal B"].article_count == 2
    assert stats["Journal B"].manual_review_count >= 1


# --- business_rule_statistics ---


def test_business_rule_statistics_track_journal_trigger_rate(mixed_reports: list) -> None:
    records = corpus_analyzer.build_corpus(mixed_reports)
    stats = business_rule_statistics.compute_business_rule_statistics(records)

    assert stats["BR-016"].trigger_rate_for("Journal A") == pytest.approx(0.5)
    assert stats["BR-011"].ever_fatal is True
    assert stats["BR-001"].unused is True


# --- recovery_statistics ---


def test_recovery_statistics_compute_clean_success_rate(mixed_reports: list) -> None:
    records = corpus_analyzer.build_corpus(mixed_reports)
    stats = recovery_statistics.compute_recovery_rule_statistics(records)

    assert stats["RR-004"].occurrences == 1
    assert stats["RR-004"].clean_success_rate == 1.0
    assert stats["RR-004"].dominant_confidence == "low"
    assert stats["RR-002"].is_significant_deficiency is True


# --- warning_statistics ---


def test_warning_statistics_flags_always_successful(mixed_reports: list) -> None:
    records = corpus_analyzer.build_corpus(mixed_reports)
    stats = {s.code: s for s in warning_statistics.compute_warning_statistics(records)}

    assert stats["CODE_BR-016"].always_successful is True
    # BR-011's warning only exists on partial-1 (a real EngineWarning); the failed
    # article's BR-011 finding comes from the raised exception, which never
    # produces an EngineWarning at all — so this pattern is still "always successful".
    assert stats["CODE_BR-011"].always_successful is True


# --- confidence_statistics ---


def test_confidence_statistics_average_and_median(mixed_reports: list) -> None:
    records = corpus_analyzer.build_corpus(mixed_reports)
    stats = confidence_statistics.compute_confidence_statistics(records)

    assert stats.average_score >= 0
    assert "Journal A" in stats.average_by_journal


# --- recommendation_engine ---


def test_business_rule_downgrade_recommendation_fires_on_real_evidence() -> None:
    reports = [
        _report(
            f"a{i}",
            "Journal A",
            status=PackageStatus.CERTIFIED_WITH_WARNINGS,
            warnings=(
                _warning(
                    rule_id="BR-100",
                    recovery_rule_id=None,
                    confidence=ConfidenceLevel.MEDIUM,
                    is_recovery=False,
                ),
            ),
        )
        for i in range(6)
    ]
    records = corpus_analyzer.build_corpus(reports)
    br_stats = business_rule_statistics.compute_business_rule_statistics(records)

    recs = recommendation_engine._business_rule_downgrade_recommendations(br_stats)

    assert any(r.id == "br-downgrade-BR-100-Journal A" for r in recs)
    rec = next(r for r in recs if r.id == "br-downgrade-BR-100-Journal A")
    assert rec.evidence["trigger_rate"] == 1.0
    assert rec.evidence["ever_fatal"] is False


def test_business_rule_downgrade_recommendation_skipped_below_sample_size() -> None:
    reports = [
        _report(
            f"a{i}",
            "Journal A",
            warnings=(
                _warning(
                    rule_id="BR-100",
                    recovery_rule_id=None,
                    confidence=ConfidenceLevel.MEDIUM,
                    is_recovery=False,
                ),
            ),
        )
        for i in range(2)
    ]
    records = corpus_analyzer.build_corpus(reports)
    br_stats = business_rule_statistics.compute_business_rule_statistics(records)

    recs = recommendation_engine._business_rule_downgrade_recommendations(br_stats)

    assert recs == []


def test_recovery_rule_upgrade_recommendation_fires_on_real_evidence() -> None:
    reports = [
        _report(
            f"a{i}",
            "Journal A",
            status=PackageStatus.CERTIFIED_WITH_RECOVERY,
            warnings=(
                _warning(
                    rule_id="BR-016",
                    recovery_rule_id="RR-004",
                    confidence=ConfidenceLevel.LOW,
                    is_recovery=True,
                ),
            ),
        )
        for i in range(12)
    ]
    records = corpus_analyzer.build_corpus(reports)
    rr_stats = recovery_statistics.compute_recovery_rule_statistics(records)

    recs = recommendation_engine._recovery_rule_confidence_upgrade_recommendations(rr_stats)

    assert any(r.id == "rr-upgrade-RR-004" for r in recs)
    rec = next(r for r in recs if r.id == "rr-upgrade-RR-004")
    assert rec.evidence["current_confidence"] == "low"
    assert rec.evidence["proposed_confidence"] == "medium"


def test_recovery_rule_upgrade_excludes_significant_deficiency_rule() -> None:
    reports = [
        _report(
            f"a{i}",
            "Journal A",
            status=PackageStatus.PARTIAL_CERTIFICATION,
            warnings=(
                _warning(
                    rule_id="BR-011",
                    recovery_rule_id="RR-002",
                    confidence=ConfidenceLevel.MEDIUM,
                    is_recovery=True,
                ),
            ),
        )
        for i in range(12)
    ]
    records = corpus_analyzer.build_corpus(reports)
    rr_stats = recovery_statistics.compute_recovery_rule_statistics(records)

    recs = recommendation_engine._recovery_rule_confidence_upgrade_recommendations(rr_stats)

    assert recs == []


def test_warning_suppression_recommendation_fires_on_real_evidence() -> None:
    reports = [
        _report(
            f"a{i}",
            "Journal A",
            status=PackageStatus.CERTIFIED_WITH_WARNINGS,
            warnings=(
                _warning(
                    rule_id="BR-050",
                    recovery_rule_id=None,
                    confidence=ConfidenceLevel.MEDIUM,
                    is_recovery=False,
                ),
            ),
        )
        for i in range(60)
    ]
    records = corpus_analyzer.build_corpus(reports)
    warn_stats = warning_statistics.compute_warning_statistics(records)

    recs = recommendation_engine._warning_suppression_recommendations(warn_stats)

    assert any(r.category == "warning" for r in recs)


def test_no_recommendations_on_clean_corpus() -> None:
    reports = [_report(f"a{i}", "Journal A") for i in range(6)]
    records = corpus_analyzer.build_corpus(reports)
    journal_stats = journal_statistics.compute_journal_statistics(records)
    br_stats = business_rule_statistics.compute_business_rule_statistics(records)
    rr_stats = recovery_statistics.compute_recovery_rule_statistics(records)
    warn_stats = warning_statistics.compute_warning_statistics(records)

    recs = recommendation_engine.generate_recommendations(
        records, journal_stats, br_stats, rr_stats, warn_stats
    )

    assert recs == []
    text = recommendation_engine.render_recommendations(recs)
    assert "No recommendation met" in text


# --- trend_analyzer ---


def test_trend_analyzer_reports_insufficient_history_for_one_snapshot(mixed_reports: list) -> None:
    records = corpus_analyzer.build_corpus(mixed_reports)
    trends = trend_analyzer.build_trends_json([trend_analyzer.BatchSnapshot("run-1", records)])

    assert trends["status"] == "insufficient_history"
    assert len(trends["points"]) == 1


def test_trend_analyzer_computes_deltas_across_two_snapshots(mixed_reports: list) -> None:
    records = corpus_analyzer.build_corpus(mixed_reports)
    snapshots = [
        trend_analyzer.BatchSnapshot("run-1", records),
        trend_analyzer.BatchSnapshot("run-2", records),
    ]

    trends = trend_analyzer.build_trends_json(snapshots)

    assert trends["status"] == "computed"
    assert trends["deltas"][0]["confidence_score_delta"] == 0
