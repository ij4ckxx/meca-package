"""Per-journal statistics and Journal_Health_Report.html — Milestone 14."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from html import escape
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.reporting.intelligence.corpus_analyzer import ArticleRecord


@dataclass(frozen=True)
class JournalStats:
    """One journal's aggregated statistics across the batch."""

    journal: str
    article_count: int
    status_counts: dict[str, int] = field(default_factory=dict)
    confidence_distribution: dict[str, int] = field(default_factory=dict)
    average_confidence_score: float = 0.0
    recovery_rule_counts: dict[str, int] = field(default_factory=dict)
    business_rule_failure_counts: dict[str, int] = field(default_factory=dict)
    manual_review_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Render as a plain, ``json.dumps``-ready dict."""
        return {
            "journal": self.journal,
            "article_count": self.article_count,
            "status_counts": self.status_counts,
            "confidence_distribution": self.confidence_distribution,
            "average_confidence_score": round(self.average_confidence_score, 1),
            "recovery_rule_counts": self.recovery_rule_counts,
            "business_rule_failure_counts": self.business_rule_failure_counts,
            "manual_review_count": self.manual_review_count,
        }


def compute_journal_statistics(records: tuple[ArticleRecord, ...]) -> dict[str, JournalStats]:
    """Compute one :class:`JournalStats` per distinct journal in ``records``."""
    by_journal: dict[str, list[ArticleRecord]] = {}
    for record in records:
        by_journal.setdefault(record.journal, []).append(record)

    result: dict[str, JournalStats] = {}
    for journal, journal_records in by_journal.items():
        status_counts: Counter[str] = Counter(r.status for r in journal_records)
        confidence_distribution: Counter[str] = Counter(
            r.overall_confidence for r in journal_records
        )
        recovery_rule_counts: Counter[str] = Counter()
        business_rule_failure_counts: Counter[str] = Counter()
        for record in journal_records:
            for rule_id in record.recovery_rules_triggered:
                recovery_rule_counts[rule_id] += 1
            for rule_id in record.business_rules_failed:
                business_rule_failure_counts[rule_id] += 1

        result[journal] = JournalStats(
            journal=journal,
            article_count=len(journal_records),
            status_counts=dict(status_counts),
            confidence_distribution=dict(confidence_distribution),
            average_confidence_score=(
                sum(r.confidence_score for r in journal_records) / len(journal_records)
            ),
            recovery_rule_counts=dict(recovery_rule_counts),
            business_rule_failure_counts=dict(business_rule_failure_counts),
            manual_review_count=sum(1 for r in journal_records if r.requires_manual_review),
        )
    return result


def render_journal_health_report(records: tuple[ArticleRecord, ...]) -> str:
    """Render ``Journal_Health_Report.html`` for a batch of articles."""
    stats = compute_journal_statistics(records)
    rows = "".join(_journal_row(s) for s in sorted(stats.values(), key=lambda s: -s.article_count))
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        "<title>Journal Health Report</title>"
        "<style>body{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;"
        "margin:2rem auto;max-width:960px;color:#1a1a1a;line-height:1.5}"
        "table{border-collapse:collapse;width:100%;margin:0.5rem 0 1rem}"
        "th,td{text-align:left;padding:0.4rem 0.6rem;border-bottom:1px solid #eee;"
        "font-size:0.92rem}th{background:#fafafa}</style></head><body>"
        "<h1>Journal Health Report</h1>"
        "<table><tr><th>Journal</th><th>Articles</th><th>Avg Confidence</th>"
        "<th>Manual Review</th><th>Top Recovery Rules</th><th>Top Business Rule Issues</th></tr>"
        f"{rows}</table></body></html>\n"
    )


def _journal_row(stats: JournalStats) -> str:
    top_recovery = _top_n(stats.recovery_rule_counts, 3)
    top_business = _top_n(stats.business_rule_failure_counts, 3)
    return (
        f"<tr><td>{escape(stats.journal)}</td><td>{stats.article_count}</td>"
        f"<td>{stats.average_confidence_score:.1f}</td><td>{stats.manual_review_count}</td>"
        f"<td>{escape(top_recovery)}</td><td>{escape(top_business)}</td></tr>"
    )


def _top_n(counts: dict[str, int], n: int) -> str:
    if not counts:
        return "—"
    ranked = sorted(counts.items(), key=lambda item: -item[1])[:n]
    return ", ".join(f"{rule_id} ({count})" for rule_id, count in ranked)


def write_journal_health_report(records: tuple[ArticleRecord, ...], output_path: Path) -> None:
    """Render and write ``Journal_Health_Report.html`` to disk."""
    output_path.write_text(render_journal_health_report(records), encoding="utf-8")
