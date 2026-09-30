"""Executive Summary — Migration_Summary.html (Milestone 13).

A corpus-level HTML summary for a batch run, built from
:class:`~meca_engine.reporting.aggregation.MigrationStatistics`. Plain
semantic HTML, no JavaScript, no external assets.
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

from meca_engine.reporting.aggregation import aggregate

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.packaging.conversion_report import ConversionReport
    from meca_engine.reporting.aggregation import MigrationStatistics

_CSS = """
body { font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; }
body { margin: 2rem auto; max-width: 900px; color: #1a1a1a; line-height: 1.5; }
h1 { font-size: 1.6rem; border-bottom: 2px solid #ddd; padding-bottom: 0.5rem; }
h2 { font-size: 1.15rem; margin-top: 2rem; color: #333; }
table { border-collapse: collapse; width: 100%; margin: 0.5rem 0 1rem; }
th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #eee; }
th, td { font-size: 0.92rem; }
th { background: #fafafa; }
.stat { display: inline-block; margin: 0 1.5rem 0.5rem 0; }
.stat .n { font-size: 1.6rem; font-weight: 700; display: block; }
.stat .label { color: #666; font-size: 0.85rem; }
"""

_STATUS_ORDER = (
    "certified",
    "certified_with_warnings",
    "certified_with_recovery",
    "partial_certification",
    "engine_failure",
    "fatal_failure",
)
_STATUS_LABELS = {
    "certified": "Certified",
    "certified_with_warnings": "Certified With Warnings",
    "certified_with_recovery": "Certified With Recovery",
    "partial_certification": "Partial Certification",
    "engine_failure": "Engine Failure",
    "fatal_failure": "Fatal Failure",
}


def render_migration_summary(reports: list[ConversionReport]) -> str:
    """Render the Executive Summary for a batch of Conversion Reports as HTML."""
    stats = aggregate(reports)
    sections = [
        _header(stats),
        _status_stats(stats),
        _confidence_stats(stats),
        _recovery_rule_stats(stats),
        _business_rule_stats(stats),
        _failure_reasons(stats),
        _journal_breakdown(stats),
    ]
    body = "\n".join(sections)
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>Migration Summary</title><style>{_CSS}</style></head>"
        f"<body>\n{body}\n</body></html>\n"
    )


def write_migration_summary(reports: list[ConversionReport], output_path: Path) -> None:
    """Render and write the Executive Summary to disk."""
    output_path.write_text(render_migration_summary(reports), encoding="utf-8")


def _header(stats: MigrationStatistics) -> str:
    return (
        "<h1>Migration Summary</h1>"
        f"<p>Total articles processed: <strong>{stats.total_articles}</strong></p>"
    )


def _status_stats(stats: MigrationStatistics) -> str:
    cards = "".join(
        f'<div class="stat"><span class="n">{stats.status_counts.get(status, 0)}</span>'
        f'<span class="label">{escape(_STATUS_LABELS[status])}</span></div>'
        for status in _STATUS_ORDER
    )
    return f"<h2>Status Distribution</h2><div>{cards}</div>"


def _confidence_stats(stats: MigrationStatistics) -> str:
    rows = "".join(
        f"<tr><td>{escape(level.upper())}</td><td>{count}</td></tr>"
        for level, count in sorted(stats.confidence_distribution.items())
    )
    return (
        "<h2>Confidence Distribution</h2>"
        f"<table><tr><th>Level</th><th>Articles</th></tr>{rows}</table>"
    )


def _recovery_rule_stats(stats: MigrationStatistics) -> str:
    if not stats.recovery_rule_occurrences:
        return "<h2>Recovery Rule Usage</h2><p>No recoveries were applied in this batch.</p>"
    rows = "".join(
        f"<tr><td>{escape(rule_id)}</td><td>{count}</td></tr>"
        for rule_id, count in sorted(
            stats.recovery_rule_occurrences.items(), key=lambda item: -item[1]
        )
    )
    return (
        "<h2>Recovery Rule Usage</h2>"
        f"<table><tr><th>Recovery Rule</th><th>Occurrences</th></tr>{rows}</table>"
    )


def _business_rule_stats(stats: MigrationStatistics) -> str:
    triggered = [usage for usage in stats.business_rule_usage.values() if not usage.unused]
    triggered.sort(key=lambda usage: -usage.triggered)
    rows = "".join(
        f"<tr><td>{escape(u.rule_id)}</td><td>{u.triggered}</td><td>{u.recovered}</td>"
        f"<td>{u.warning}</td><td>{u.fatal}</td></tr>"
        for u in triggered
    )
    if not rows:
        return (
            "<h2>Business Rule Warning Statistics</h2><p>No Business Rule deviations observed.</p>"
        )
    return (
        "<h2>Business Rule Warning Statistics</h2>"
        "<table><tr><th>Rule</th><th>Triggered</th><th>Recovered</th>"
        f"<th>Warning</th><th>Fatal</th></tr>{rows}</table>"
    )


def _failure_reasons(stats: MigrationStatistics) -> str:
    if not stats.failure_reason_counts:
        return "<h2>Top Failure Reasons</h2><p>No failures in this batch.</p>"
    rows = "".join(
        f"<tr><td>{escape(reason)}</td><td>{count}</td></tr>"
        for reason, count in sorted(stats.failure_reason_counts.items(), key=lambda item: -item[1])
    )
    return (
        f"<h2>Top Failure Reasons</h2><table><tr><th>Reason</th><th>Count</th></tr>{rows}</table>"
    )


def _journal_breakdown(stats: MigrationStatistics) -> str:
    rows = "".join(
        f"<tr><td>{escape(journal)}</td><td>{count}</td>"
        f"<td>{stats.journal_recovery_counts.get(journal, 0)}</td></tr>"
        for journal, count in sorted(stats.journal_article_counts.items())
    )
    return (
        "<h2>Journal Breakdown</h2>"
        "<table><tr><th>Journal</th><th>Articles</th><th>Recoveries</th></tr>"
        f"{rows}</table>"
    )
