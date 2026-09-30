"""migration_dashboard.json — Milestone 13.

Everything a future web dashboard would need, as plain JSON-ready data.
No dashboard is built here — this module only assembles the data.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from meca_engine.reporting.aggregation import aggregate

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.packaging.conversion_report import ConversionReport


def build_dashboard_data(reports: list[ConversionReport]) -> dict[str, Any]:
    """Assemble the full dashboard-ready data structure for a batch."""
    stats = aggregate(reports)
    return {
        "generated_at": None,
        "summary": {
            "total_articles": stats.total_articles,
            "status_counts": dict(stats.status_counts),
            "confidence_distribution": dict(stats.confidence_distribution),
        },
        "recovery_rule_usage": dict(stats.recovery_rule_occurrences),
        "business_rule_usage": {
            rule_id: {
                "triggered": usage.triggered,
                "recovered": usage.recovered,
                "warning": usage.warning,
                "fatal": usage.fatal,
                "unused": usage.unused,
            }
            for rule_id, usage in stats.business_rule_usage.items()
        },
        "journals": {
            journal: {
                "articles": count,
                "recoveries": stats.journal_recovery_counts.get(journal, 0),
            }
            for journal, count in stats.journal_article_counts.items()
        },
        "failure_reasons": dict(stats.failure_reason_counts),
        "articles": [_article_summary(report) for report in reports],
    }


def _article_summary(report: ConversionReport) -> dict[str, Any]:
    return {
        "article_id": report.article_id,
        "journal": report.journal,
        "status": report.status.value,
        "confidence_score": report.confidence_score,
        "overall_confidence": report.overall_confidence.value,
        "recovery_count": len(report.recoveries),
        "warning_count": len(report.warnings) + len(report.generator_findings),
        "recovery_rules_applied": list(report.recovery_rules_applied),
        "missing_files": list(report.missing_files),
        "missing_metadata": list(report.missing_metadata),
        "generated": report.unrecoverable_error is None,
    }


def write_dashboard_json(reports: list[ConversionReport], output_path: Path) -> None:
    """Assemble and write ``migration_dashboard.json`` to disk."""
    output_path.write_text(json.dumps(build_dashboard_data(reports), indent=2), encoding="utf-8")
