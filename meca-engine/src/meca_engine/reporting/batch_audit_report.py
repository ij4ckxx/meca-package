"""Batch Audit Report — Migration Audit / Traceability milestone.

One consolidated HTML page for a whole batch, built entirely from
already-computed intelligence data
(:mod:`meca_engine.reporting.intelligence`) — no statistic here is
recomputed differently from what ``Business_Rule_Effectiveness.md``,
``Recovery_Rule_Effectiveness.md``, ``Confidence_Analysis.md``, and
``Journal_Health_Report.html`` already show; this module only lays them
out together. The one genuinely new aggregation is DTD pass/fail counts
per file type, computed directly from each report's own
``validation_report`` (real, existing data).
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.packaging.conversion_report import ConversionReport
    from meca_engine.reporting.intelligence.business_rule_statistics import BusinessRuleStats
    from meca_engine.reporting.intelligence.confidence_statistics import ConfidenceStats
    from meca_engine.reporting.intelligence.corpus_analyzer import ArticleRecord
    from meca_engine.reporting.intelligence.journal_statistics import JournalStats
    from meca_engine.reporting.intelligence.recovery_statistics import RecoveryRuleStats

_CSS = """
body { font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; }
body { margin: 2rem auto; max-width: 960px; color: #1a1a1a; line-height: 1.5; }
h1 { font-size: 1.5rem; border-bottom: 2px solid #ddd; padding-bottom: 0.5rem; }
h2 { font-size: 1.1rem; margin-top: 2rem; color: #333; }
table { border-collapse: collapse; width: 100%; margin: 0.5rem 0 1rem; }
th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #eee; }
th, td { font-size: 0.92rem; }
th { background: #fafafa; }
.stat-grid { display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 0.5rem 0 1rem; }
.stat-card { border: 1px solid #ddd; border-radius: 6px; padding: 0.6rem 0.9rem; min-width: 120px; }
.stat-value { font-size: 1.4rem; font-weight: 700; }
.stat-label { color: #666; font-size: 0.85rem; }
.empty { color: #888; font-style: italic; }
"""


def _dtd_stats(reports: list[ConversionReport]) -> dict[str, dict[str, int]]:
    """Pass/warning/error/not-checked counts per generated file type."""
    stats: dict[str, dict[str, int]] = {}
    for report in reports:
        validation = report.validation_report
        if validation is None:
            continue
        for file_report in validation.files:
            suffix = file_report.filename.rsplit("_", 1)[-1]
            bucket = stats.setdefault(
                suffix, {"pass": 0, "warning": 0, "error": 0, "not_checked": 0}
            )
            result = file_report.dtd_result.value if file_report.dtd_result else "not_checked"
            bucket[result] += 1
    return stats


def _top_source_problems(
    records: tuple[ArticleRecord, ...], limit: int = 10
) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for record in records:
        for item in (*record.missing_metadata, *record.missing_files):
            counts[item] = counts.get(item, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])[:limit]


def _top_manual_review_reasons(
    reports: list[ConversionReport], limit: int = 10
) -> list[tuple[str, int]]:
    from meca_engine.reporting.csv_reports import build_manual_review_rows

    counts: dict[str, int] = {}
    for row in build_manual_review_rows(reports):
        counts[row["Reason"]] = counts.get(row["Reason"], 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])[:limit]


def render_batch_audit_report(
    reports: list[ConversionReport],
    records: tuple[ArticleRecord, ...],
    journal_stats: dict[str, JournalStats],
    business_rule_stats: dict[str, BusinessRuleStats],
    recovery_rule_stats: dict[str, RecoveryRuleStats],
    confidence_stats: ConfidenceStats,
) -> str:
    """Render the whole batch's Batch Audit Report as a self-contained HTML string."""
    status_counts: dict[str, int] = {}
    for report in reports:
        status_counts[report.status.value] = status_counts.get(report.status.value, 0) + 1

    overview_cards = "".join(
        f'<div class="stat-card"><div class="stat-value">{value}</div>'
        f'<div class="stat-label">{escape(label)}</div></div>'
        for label, value in [
            ("Total Packages", len(reports)),
            ("Certified", status_counts.get("certified", 0)),
            ("Certified With Warnings", status_counts.get("certified_with_warnings", 0)),
            ("Recovered", status_counts.get("certified_with_recovery", 0)),
            ("Partial Certification", status_counts.get("partial_certification", 0)),
            ("Engine Failures", status_counts.get("engine_failure", 0)),
            ("Fatal Failures", status_counts.get("fatal_failure", 0)),
        ]
    )

    dtd = _dtd_stats(reports)
    dtd_rows = "".join(
        f"<tr><td>{escape(filetype)}</td><td>{counts['pass']}</td><td>{counts['warning']}</td>"
        f"<td>{counts['error']}</td><td>{counts['not_checked']}</td></tr>"
        for filetype, counts in sorted(dtd.items())
    )

    br_rows = "".join(
        f"<tr><td>{escape(s.rule_id)}</td><td>{s.total_triggered}</td>"
        f"<td>{s.total_recovered}</td><td>{s.total_failed}</td></tr>"
        for s in sorted(business_rule_stats.values(), key=lambda s: -s.total_triggered)
        if not s.unused
    )

    rr_rows = "".join(
        f"<tr><td>{escape(s.rule_id)}</td><td>{s.occurrences}</td>"
        f"<td>{s.articles_affected}</td><td>{round(s.clean_success_rate * 100, 1)}%</td></tr>"
        for s in sorted(recovery_rule_stats.values(), key=lambda s: -s.occurrences)
        if s.occurrences > 0
    )

    source_rows = "".join(
        f"<tr><td>{escape(item)}</td><td>{count}</td></tr>"
        for item, count in _top_source_problems(records)
    )

    review_rows = "".join(
        f"<tr><td>{escape(reason)}</td><td>{count}</td></tr>"
        for reason, count in _top_manual_review_reasons(reports)
    )

    journal_rows = "".join(
        f"<tr><td>{escape(j.journal)}</td><td>{j.article_count}</td>"
        f"<td>{round(j.average_confidence_score, 1)}</td><td>{j.manual_review_count}</td></tr>"
        for j in sorted(journal_stats.values(), key=lambda j: -j.article_count)
    )

    confidence_rows = "".join(
        f"<tr><td>{escape(level)}</td><td>{count}</td></tr>"
        for level, count in confidence_stats.distribution.items()
    )

    body = f"""
<h1>Batch Audit Report</h1>
<h2>Overview</h2>
<div class="stat-grid">{overview_cards}</div>

<h2>DTD Statistics</h2>
<table><tr><th>File Type</th><th>Pass</th><th>Warning</th><th>Error</th><th>Not Checked</th></tr>
{dtd_rows or '<tr><td colspan="5" class="empty">No validation data.</td></tr>'}</table>

<h2>Business Rule Statistics</h2>
<table><tr><th>Rule</th><th>Triggered</th><th>Recovered</th><th>Failed</th></tr>
{br_rows or '<tr><td colspan="4" class="empty">No Business Rules triggered.</td></tr>'}</table>

<h2>Recovery Statistics</h2>
<table><tr><th>Rule</th><th>Occurrences</th><th>Articles Affected</th>
<th>Clean Success Rate</th></tr>
{rr_rows or '<tr><td colspan="4" class="empty">No Recovery Rules applied.</td></tr>'}</table>

<h2>Top Source Problems</h2>
<table><tr><th>Problem</th><th>Occurrences</th></tr>
{source_rows or '<tr><td colspan="2" class="empty">None.</td></tr>'}</table>

<h2>Top Manual Review Reasons</h2>
<table><tr><th>Reason</th><th>Occurrences</th></tr>
{review_rows or '<tr><td colspan="2" class="empty">None.</td></tr>'}</table>

<h2>Journal Comparison</h2>
<table><tr><th>Journal</th><th>Articles</th><th>Avg. Confidence</th><th>Manual Review</th></tr>
{journal_rows or '<tr><td colspan="4" class="empty">No journals.</td></tr>'}</table>

<h2>Confidence Distribution</h2>
<table><tr><th>Level</th><th>Articles</th></tr>
{confidence_rows or '<tr><td colspan="2" class="empty">No data.</td></tr>'}</table>
"""
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>Batch Audit Report</title><style>{_CSS}</style></head>"
        f"<body>\n{body}\n</body></html>\n"
    )


def write_batch_audit_report(
    reports: list[ConversionReport],
    records: tuple[ArticleRecord, ...],
    journal_stats: dict[str, JournalStats],
    business_rule_stats: dict[str, BusinessRuleStats],
    recovery_rule_stats: dict[str, RecoveryRuleStats],
    confidence_stats: ConfidenceStats,
    output_path: Path,
) -> None:
    """Render and write the whole batch's Batch Audit Report to disk."""
    output_path.write_text(
        render_batch_audit_report(
            reports,
            records,
            journal_stats,
            business_rule_stats,
            recovery_rule_stats,
            confidence_stats,
        ),
        encoding="utf-8",
    )
