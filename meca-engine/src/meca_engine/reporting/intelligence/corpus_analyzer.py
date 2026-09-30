"""Corpus loading and normalization — Milestone 14.

Every other intelligence module builds on :func:`build_corpus`'s output —
one :class:`ArticleRecord` per article, collecting exactly the fields the
product owner needs (journal, status, confidence, recovery rules
triggered, warnings, business rules failed/recovered, missing
metadata/files, skipped files, generated files, manual-review flag) —
derived entirely from an already-built
:class:`~meca_engine.packaging.conversion_report.ConversionReport`. No
validation is re-run and no new signal is invented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from meca_engine.reporting.csv_reports import build_manual_review_rows

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.packaging.conversion_report import ConversionReport

# Statuses under which a package still exists (as opposed to
# ENGINE_FAILURE/FATAL_FAILURE, where no package was produced at all).
SUCCESSFUL_STATUSES = frozenset(
    {"certified", "certified_with_warnings", "certified_with_recovery", "partial_certification"}
)
FAILURE_STATUSES = frozenset({"engine_failure", "fatal_failure"})


@dataclass(frozen=True)
class ArticleRecord:
    """One article's collected evidence, normalized from its Conversion Report."""

    article_id: str
    journal: str
    status: str
    confidence_score: int
    overall_confidence: str
    recovery_rules_triggered: tuple[str, ...]
    warning_count: int
    business_rules_failed: tuple[str, ...]
    business_rules_recovered: tuple[str, ...]
    missing_metadata: tuple[str, ...]
    missing_files: tuple[str, ...]
    skipped_files: tuple[str, ...]
    generated_files: tuple[str, ...]
    requires_manual_review: bool
    source: ConversionReport = field(repr=False, compare=False)

    @property
    def succeeded(self) -> bool:
        """Whether a package actually exists for this article."""
        return self.status in SUCCESSFUL_STATUSES


def build_corpus(reports: list[ConversionReport]) -> tuple[ArticleRecord, ...]:
    """Build one :class:`ArticleRecord` per Conversion Report.

    The shared input every other intelligence module reads.
    """
    manual_review_articles = {row["Article"] for row in build_manual_review_rows(reports)}
    return tuple(_to_record(report, manual_review_articles) for report in reports)


def _to_record(report: ConversionReport, manual_review_articles: set[str]) -> ArticleRecord:
    recovered_rule_ids = {w.rule_id for w in report.recoveries if w.rule_id}
    all_finding_rule_ids = {f.rule_id for f in report.business_rule_findings}
    failed_rule_ids = all_finding_rule_ids - recovered_rule_ids
    return ArticleRecord(
        article_id=report.article_id,
        journal=report.journal or "Unknown",
        status=report.status.value,
        confidence_score=report.confidence_score,
        overall_confidence=report.overall_confidence.value,
        recovery_rules_triggered=report.recovery_rules_applied,
        warning_count=len(report.warnings) + len(report.generator_findings),
        business_rules_failed=tuple(sorted(failed_rule_ids)),
        business_rules_recovered=tuple(sorted(recovered_rule_ids)),
        missing_metadata=report.missing_metadata,
        missing_files=report.missing_files,
        skipped_files=report.skipped_files,
        generated_files=report.generated_files,
        requires_manual_review=report.article_id in manual_review_articles,
        source=report,
    )


def render_migration_intelligence_report(reports: list[ConversionReport]) -> str:
    """Render ``Migration_Intelligence_Report.html`` — the top-level combined view.

    Deliberately thin: pulls one headline metric from each of the other 7
    intelligence modules rather than re-deriving anything, so this stays
    a summary-of-summaries, not a second computation path.
    """
    from html import escape

    from meca_engine.reporting.intelligence import (
        business_rule_statistics,
        confidence_statistics,
        journal_statistics,
        recommendation_engine,
        recovery_statistics,
        warning_statistics,
    )

    records = build_corpus(reports)
    journal_stats = journal_statistics.compute_journal_statistics(records)
    br_stats = business_rule_statistics.compute_business_rule_statistics(records)
    rr_stats = recovery_statistics.compute_recovery_rule_statistics(records)
    warn_stats = warning_statistics.compute_warning_statistics(records)
    conf_stats = confidence_statistics.compute_confidence_statistics(records)
    recommendations = recommendation_engine.generate_recommendations(
        records, journal_stats, br_stats, rr_stats, warn_stats
    )

    total = len(records)
    succeeded = sum(1 for r in records if r.succeeded)
    manual_review = sum(1 for r in records if r.requires_manual_review)
    br_used = sum(1 for s in br_stats.values() if s.total_triggered > 0)
    rr_used = sum(1 for s in rr_stats.values() if s.occurrences > 0)
    warn_distinct = len(warn_stats)

    rows = "".join(
        f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>"
        for k, v in [
            ("Total articles analyzed", total),
            ("Packages generated", f"{succeeded}/{total}"),
            ("Journals covered", len(journal_stats)),
            ("Business Rules with observed activity", br_used),
            ("Recovery Rules applied", rr_used),
            ("Distinct warning patterns", warn_distinct),
            ("Average confidence score", f"{conf_stats.average_score:.1f}/100"),
            ("Articles flagged for manual review", manual_review),
            ("Recommendations generated", len(recommendations)),
        ]
    )
    rec_items = (
        "".join(
            f"<li><strong>{escape(r.title)}</strong> — {escape(r.rationale)}</li>"
            for r in recommendations
        )
        or "<li>No recommendations met the evidence thresholds for this batch.</li>"
    )

    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        "<title>Migration Intelligence Report</title>"
        "<style>body{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;"
        "margin:2rem auto;max-width:900px;color:#1a1a1a;line-height:1.5}"
        "table{border-collapse:collapse;width:100%;margin:0.5rem 0 1rem}"
        "th,td{text-align:left;padding:0.4rem 0.6rem;border-bottom:1px solid #eee}"
        "th{background:#fafafa}</style></head><body>"
        "<h1>Migration Intelligence Report</h1>"
        f"<table>{rows}</table>"
        "<h2>Top Recommendations</h2>"
        f"<ul>{rec_items}</ul>"
        "</body></html>\n"
    )


def write_migration_intelligence_report(reports: list[ConversionReport], output_path: Path) -> None:
    """Render and write ``Migration_Intelligence_Report.html`` to disk."""
    output_path.write_text(render_migration_intelligence_report(reports), encoding="utf-8")


def build_dashboard_intelligence(reports: list[ConversionReport]) -> dict[str, Any]:
    """Assemble ``dashboard_intelligence.json`` — everything a future dashboard needs."""
    from meca_engine.reporting.intelligence import (
        business_rule_statistics,
        confidence_statistics,
        journal_statistics,
        recommendation_engine,
        recovery_statistics,
        warning_statistics,
    )

    records = build_corpus(reports)
    journal_stats = journal_statistics.compute_journal_statistics(records)
    br_stats = business_rule_statistics.compute_business_rule_statistics(records)
    rr_stats = recovery_statistics.compute_recovery_rule_statistics(records)
    warn_stats = warning_statistics.compute_warning_statistics(records)
    conf_stats = confidence_statistics.compute_confidence_statistics(records)
    recommendations = recommendation_engine.generate_recommendations(
        records, journal_stats, br_stats, rr_stats, warn_stats
    )

    return {
        "total_articles": len(records),
        "journals": {name: stats.to_dict() for name, stats in journal_stats.items()},
        "business_rules": {
            rid: stats.to_dict() for rid, stats in br_stats.items() if stats.total_triggered > 0
        },
        "recovery_rules": {
            rid: stats.to_dict() for rid, stats in rr_stats.items() if stats.occurrences > 0
        },
        "warnings": [stats.to_dict() for stats in warn_stats],
        "confidence": conf_stats.to_dict(),
        "package_status": {
            record.article_id: {"status": record.status, "journal": record.journal}
            for record in records
        },
        "manual_review": [r.article_id for r in records if r.requires_manual_review],
        "recommendations": [r.to_dict() for r in recommendations],
    }
