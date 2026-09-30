"""Per-Recovery-Rule effectiveness statistics — Milestone 14."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from meca_engine.model.recovery_rules import ALL_RECOVERY_RULES, SIGNIFICANT_DEFICIENCY_RULE_IDS

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.reporting.intelligence.corpus_analyzer import ArticleRecord


@dataclass(frozen=True)
class RecoveryRuleStats:
    """One Recovery Rule's observed effectiveness across the batch."""

    rule_id: str
    occurrences: int
    articles_affected: int
    is_significant_deficiency: bool
    failure_correlated_articles: (
        int  # articles using this rule that ended ENGINE_FAILURE/FATAL_FAILURE
    )
    partial_certification_articles: int
    observed_confidence_levels: dict[str, int] = field(default_factory=dict)

    @property
    def clean_success_rate(self) -> float:
        """Fraction of affected articles with no downstream engine/fatal failure."""
        if self.articles_affected == 0:
            return 0.0
        return 1 - (self.failure_correlated_articles / self.articles_affected)

    @property
    def dominant_confidence(self) -> str | None:
        """The single confidence level most instances of this rule were recorded with."""
        if not self.observed_confidence_levels:
            return None
        return max(
            self.observed_confidence_levels,
            key=lambda level: self.observed_confidence_levels[level],
        )

    def to_dict(self) -> dict[str, Any]:
        """Render as a plain, ``json.dumps``-ready dict."""
        return {
            "rule_id": self.rule_id,
            "occurrences": self.occurrences,
            "articles_affected": self.articles_affected,
            "is_significant_deficiency": self.is_significant_deficiency,
            "failure_correlated_articles": self.failure_correlated_articles,
            "partial_certification_articles": self.partial_certification_articles,
            "clean_success_rate": round(self.clean_success_rate, 3),
            "observed_confidence_levels": self.observed_confidence_levels,
            "dominant_confidence": self.dominant_confidence,
        }


def compute_recovery_rule_statistics(
    records: tuple[ArticleRecord, ...],
) -> dict[str, RecoveryRuleStats]:
    """Compute one :class:`RecoveryRuleStats` per catalog Recovery Rule."""
    occurrences: Counter[str] = Counter()
    articles_affected: Counter[str] = Counter()
    failure_correlated: Counter[str] = Counter()
    partial_certification: Counter[str] = Counter()
    confidence_levels: dict[str, Counter[str]] = {}

    for record in records:
        affected_rule_ids = set(record.recovery_rules_triggered)
        for rule_id in affected_rule_ids:
            articles_affected[rule_id] += 1
            if record.status in ("engine_failure", "fatal_failure"):
                failure_correlated[rule_id] += 1
            if record.status == "partial_certification":
                partial_certification[rule_id] += 1
        for warning in record.source.recoveries:
            if warning.recovery_rule_id:
                occurrences[warning.recovery_rule_id] += 1
                confidence_levels.setdefault(warning.recovery_rule_id, Counter())[
                    warning.confidence.value
                ] += 1

    return {
        rule.rule_id: RecoveryRuleStats(
            rule_id=rule.rule_id,
            occurrences=occurrences[rule.rule_id],
            articles_affected=articles_affected[rule.rule_id],
            is_significant_deficiency=rule.rule_id in SIGNIFICANT_DEFICIENCY_RULE_IDS,
            failure_correlated_articles=failure_correlated[rule.rule_id],
            partial_certification_articles=partial_certification[rule.rule_id],
            observed_confidence_levels=dict(confidence_levels.get(rule.rule_id, Counter())),
        )
        for rule in ALL_RECOVERY_RULES
    }


def render_recovery_rule_effectiveness(records: tuple[ArticleRecord, ...]) -> str:
    """Render ``Recovery_Rule_Effectiveness.md`` for a batch of articles."""
    stats = compute_recovery_rule_statistics(records)
    used = sorted((s for s in stats.values() if s.occurrences > 0), key=lambda s: -s.occurrences)
    lines = [
        "# Recovery Rule Effectiveness",
        "",
        "| Rule | Occurrences | Articles | Clean Success Rate | "
        "Dominant Confidence | Significant Deficiency |",
        "|---|---|---|---|---|---|",
    ]
    for s in used:
        lines.append(
            f"| {s.rule_id} | {s.occurrences} | {s.articles_affected} | "
            f"{s.clean_success_rate:.0%} | {s.dominant_confidence or '—'} | "
            f"{'yes' if s.is_significant_deficiency else 'no'} |"
        )
    unused_count = sum(1 for s in stats.values() if s.occurrences == 0)
    lines += [
        "",
        f"**Used:** {len(used)} rules. **Unused:** {unused_count} rules "
        "(never applied in this batch).",
    ]
    return "\n".join(lines)


def write_recovery_rule_effectiveness(
    records: tuple[ArticleRecord, ...], output_path: Path
) -> None:
    """Render and write ``Recovery_Rule_Effectiveness.md`` to disk."""
    output_path.write_text(render_recovery_rule_effectiveness(records), encoding="utf-8")
