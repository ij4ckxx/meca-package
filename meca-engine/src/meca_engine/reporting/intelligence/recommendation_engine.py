"""Deterministic Recommendation Engine — Milestone 14.

Every recommendation below is produced by a fixed, documented threshold
rule applied to counted evidence — no AI, no heuristics that cannot be
traced back to a specific count/percentage. If the evidence in a given
batch does not clear a rule's threshold, that rule simply produces no
recommendation; nothing is ever invented to fill out a report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.reporting.intelligence.business_rule_statistics import BusinessRuleStats
    from meca_engine.reporting.intelligence.corpus_analyzer import ArticleRecord
    from meca_engine.reporting.intelligence.journal_statistics import JournalStats
    from meca_engine.reporting.intelligence.recovery_statistics import RecoveryRuleStats
    from meca_engine.reporting.intelligence.warning_statistics import WarningStats

# Thresholds — deliberately named constants, not magic numbers, so a
# product owner can see exactly what "common enough to act on" means.
# Calibrated for a corpus in the tens-to-hundreds of articles; revisit
# once real production volume (thousands of articles) is available.
BUSINESS_RULE_DOWNGRADE_MIN_TRIGGER_RATE = 0.90
BUSINESS_RULE_DOWNGRADE_MIN_JOURNAL_ARTICLES = 5
RECOVERY_RULE_UPGRADE_MIN_OCCURRENCES = 10
WARNING_SUPPRESSION_MIN_OCCURRENCES = 50
JOURNAL_CONFIG_MIN_MISSING_METADATA_RATE = 0.80
JOURNAL_CONFIG_MIN_JOURNAL_ARTICLES = 5

_CONFIDENCE_ORDER = ("low", "medium", "high")


@dataclass(frozen=True)
class Recommendation:
    """One deterministic, evidence-backed recommendation."""

    id: str
    category: str  # "business_rule" | "recovery_rule" | "warning" | "journal_config"
    title: str
    rationale: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Render as a plain, ``json.dumps``-ready dict."""
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "rationale": self.rationale,
            "evidence": self.evidence,
        }


def generate_recommendations(
    records: tuple[ArticleRecord, ...],
    journal_stats: dict[str, JournalStats],
    business_rule_stats: dict[str, BusinessRuleStats],
    recovery_rule_stats: dict[str, RecoveryRuleStats],
    warning_stats: list[WarningStats],
) -> list[Recommendation]:
    """Run every deterministic rule and return the recommendations that clear their threshold."""
    recommendations: list[Recommendation] = []
    recommendations += _business_rule_downgrade_recommendations(business_rule_stats)
    recommendations += _recovery_rule_confidence_upgrade_recommendations(recovery_rule_stats)
    recommendations += _warning_suppression_recommendations(warning_stats)
    recommendations += _journal_metadata_config_recommendations(records)
    return recommendations


def _business_rule_downgrade_recommendations(
    business_rule_stats: dict[str, BusinessRuleStats],
) -> list[Recommendation]:
    recommendations = []
    for rule_id, stats in business_rule_stats.items():
        if stats.unused or stats.ever_fatal:
            continue
        for journal, article_count in stats.journal_article_counts.items():
            if article_count < BUSINESS_RULE_DOWNGRADE_MIN_JOURNAL_ARTICLES:
                continue
            rate = stats.trigger_rate_for(journal)
            if rate < BUSINESS_RULE_DOWNGRADE_MIN_TRIGGER_RATE:
                continue
            trigger_count = stats.journal_trigger_counts.get(journal, 0)
            recommendations.append(
                Recommendation(
                    id=f"br-downgrade-{rule_id}-{journal}",
                    category="business_rule",
                    title=f"Downgrade {rule_id} to Warning for {journal}",
                    rationale=(
                        f"{rule_id} triggered in {trigger_count}/{article_count} "
                        f"({rate:.0%}) of {journal}'s articles and never caused an "
                        "engine or fatal failure anywhere in this batch."
                    ),
                    evidence={
                        "rule_id": rule_id,
                        "journal": journal,
                        "triggered": trigger_count,
                        "total_articles": article_count,
                        "trigger_rate": round(rate, 3),
                        "ever_fatal": False,
                    },
                )
            )
    return recommendations


def _recovery_rule_confidence_upgrade_recommendations(
    recovery_rule_stats: dict[str, RecoveryRuleStats],
) -> list[Recommendation]:
    recommendations = []
    for rule_id, stats in recovery_rule_stats.items():
        if stats.occurrences < RECOVERY_RULE_UPGRADE_MIN_OCCURRENCES:
            continue
        if stats.is_significant_deficiency or stats.failure_correlated_articles > 0:
            continue
        current = stats.dominant_confidence
        if current is None or current not in _CONFIDENCE_ORDER or current == "high":
            continue
        next_level = _CONFIDENCE_ORDER[_CONFIDENCE_ORDER.index(current) + 1]
        recommendations.append(
            Recommendation(
                id=f"rr-upgrade-{rule_id}",
                category="recovery_rule",
                title=(
                    f"Increase {rule_id} confidence from {current.upper()} to {next_level.upper()}"
                ),
                rationale=(
                    f"{rule_id} was applied {stats.occurrences} times across "
                    f"{stats.articles_affected} articles with zero downstream "
                    "engine/fatal failures."
                ),
                evidence={
                    "rule_id": rule_id,
                    "occurrences": stats.occurrences,
                    "articles_affected": stats.articles_affected,
                    "failure_correlated_articles": stats.failure_correlated_articles,
                    "current_confidence": current,
                    "proposed_confidence": next_level,
                },
            )
        )
    return recommendations


def _warning_suppression_recommendations(warning_stats: list[WarningStats]) -> list[Recommendation]:
    recommendations = []
    for stats in warning_stats:
        if stats.occurrences < WARNING_SUPPRESSION_MIN_OCCURRENCES or not stats.always_successful:
            continue
        recommendations.append(
            Recommendation(
                id=f"warn-suppress-{stats.code}",
                category="warning",
                title=f"Suppress {stats.code!r} from the dashboard",
                rationale=(
                    f"This warning occurred {stats.occurrences} times across "
                    f"{stats.articles_affected} articles, and every one of them "
                    "still certified successfully."
                ),
                evidence={
                    "code": stats.code,
                    "sample_message": stats.sample_message,
                    "occurrences": stats.occurrences,
                    "articles_affected": stats.articles_affected,
                    "always_successful": stats.always_successful,
                },
            )
        )
    return recommendations


def _journal_metadata_config_recommendations(
    records: tuple[ArticleRecord, ...],
) -> list[Recommendation]:
    recommendations = []
    by_journal: dict[str, list[ArticleRecord]] = {}
    for record in records:
        by_journal.setdefault(record.journal, []).append(record)

    for journal, journal_records in by_journal.items():
        if len(journal_records) < JOURNAL_CONFIG_MIN_JOURNAL_ARTICLES:
            continue
        affected = sum(1 for r in journal_records if r.missing_metadata)
        rate = affected / len(journal_records)
        if rate < JOURNAL_CONFIG_MIN_MISSING_METADATA_RATE:
            continue
        recommendations.append(
            Recommendation(
                id=f"journal-config-{journal}",
                category="journal_config",
                title=f"Add journal-specific configuration for {journal}",
                rationale=(
                    f"{affected}/{len(journal_records)} ({rate:.0%}) of {journal}'s "
                    "articles are missing metadata the engine could not derive."
                ),
                evidence={
                    "journal": journal,
                    "affected": affected,
                    "total_articles": len(journal_records),
                    "rate": round(rate, 3),
                },
            )
        )
    return recommendations


def render_recommendations(recommendations: list[Recommendation]) -> str:
    """Render ``Recommendations.md`` for a list of recommendations."""
    if not recommendations:
        return (
            "# Recommendations\n\n"
            "No recommendation met its evidence threshold for this batch. "
            "This is expected on a small or clean corpus — thresholds are documented "
            "in `recommendation_engine.py` and re-evaluated as more data accumulates."
        )
    by_category: dict[str, list[Recommendation]] = {}
    for rec in recommendations:
        by_category.setdefault(rec.category, []).append(rec)

    lines = ["# Recommendations", ""]
    for category, items in sorted(by_category.items()):
        lines.append(f"## {category.replace('_', ' ').title()}")
        lines.append("")
        for rec in items:
            lines.append(f"### {rec.title}")
            lines.append("")
            lines.append(rec.rationale)
            lines.append("")
            lines.append("**Evidence:**")
            for key, value in rec.evidence.items():
                lines.append(f"- {key}: {value}")
            lines.append("")
    return "\n".join(lines)


def write_recommendations(recommendations: list[Recommendation], output_path: Path) -> None:
    """Render and write ``Recommendations.md`` to disk."""
    output_path.write_text(render_recommendations(recommendations), encoding="utf-8")
