"""Per-Business-Rule effectiveness statistics — Milestone 14.

Deeper than `reporting/analytics.py`'s existing Triggered/Recovered/
Warning/Fatal table: this adds a per-journal trigger rate, which is the
evidence the recommendation engine needs for its "downgrade this rule
for this journal" rule.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from meca_engine.reporting.aggregation import ALL_BUSINESS_RULE_IDS

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.reporting.intelligence.corpus_analyzer import ArticleRecord


@dataclass(frozen=True)
class BusinessRuleStats:
    """One Business Rule's observed effectiveness across the batch."""

    rule_id: str
    total_triggered: int
    total_recovered: int
    total_failed: int
    ever_fatal: bool
    journal_trigger_counts: dict[str, int] = field(default_factory=dict)
    journal_article_counts: dict[str, int] = field(default_factory=dict)

    @property
    def unused(self) -> bool:
        """Whether this rule was never referenced by any finding in the batch."""
        return self.total_triggered == 0

    def trigger_rate_for(self, journal: str) -> float:
        """Fraction of ``journal``'s articles where this rule triggered."""
        total = self.journal_article_counts.get(journal, 0)
        if total == 0:
            return 0.0
        return self.journal_trigger_counts.get(journal, 0) / total

    def to_dict(self) -> dict[str, Any]:
        """Render as a plain, ``json.dumps``-ready dict."""
        return {
            "rule_id": self.rule_id,
            "total_triggered": self.total_triggered,
            "total_recovered": self.total_recovered,
            "total_failed": self.total_failed,
            "ever_fatal": self.ever_fatal,
            "journal_trigger_rates": {
                journal: round(self.trigger_rate_for(journal), 3)
                for journal in self.journal_article_counts
            },
        }


def compute_business_rule_statistics(
    records: tuple[ArticleRecord, ...],
) -> dict[str, BusinessRuleStats]:
    """Compute one :class:`BusinessRuleStats` per Business Rule ID (BR-001..BR-160)."""
    journal_article_counts: Counter[str] = Counter(r.journal for r in records)
    triggered: Counter[str] = Counter()
    recovered: Counter[str] = Counter()
    failed: Counter[str] = Counter()
    fatal_rule_ids: set[str] = set()
    journal_trigger_counts: dict[str, Counter[str]] = {}

    for record in records:
        for rule_id in record.business_rules_recovered:
            triggered[rule_id] += 1
            recovered[rule_id] += 1
            journal_trigger_counts.setdefault(rule_id, Counter())[record.journal] += 1
        for rule_id in record.business_rules_failed:
            triggered[rule_id] += 1
            failed[rule_id] += 1
            journal_trigger_counts.setdefault(rule_id, Counter())[record.journal] += 1
        if record.status in ("engine_failure", "fatal_failure"):
            fatal_rule_ids.update(record.business_rules_failed)

    return {
        rule_id: BusinessRuleStats(
            rule_id=rule_id,
            total_triggered=triggered[rule_id],
            total_recovered=recovered[rule_id],
            total_failed=failed[rule_id],
            ever_fatal=rule_id in fatal_rule_ids,
            journal_trigger_counts=dict(journal_trigger_counts.get(rule_id, Counter())),
            journal_article_counts=dict(journal_article_counts),
        )
        for rule_id in ALL_BUSINESS_RULE_IDS
    }


def render_business_rule_effectiveness(records: tuple[ArticleRecord, ...]) -> str:
    """Render ``Business_Rule_Effectiveness.md`` for a batch of articles."""
    stats = compute_business_rule_statistics(records)
    used = sorted((s for s in stats.values() if not s.unused), key=lambda s: -s.total_triggered)
    lines = [
        "# Business Rule Effectiveness",
        "",
        "| Rule | Triggered | Recovered | Failed | Ever Fatal | Top Journal (rate) |",
        "|---|---|---|---|---|---|",
    ]
    for s in used:
        top_journal, rate = _top_journal_rate(s)
        lines.append(
            f"| {s.rule_id} | {s.total_triggered} | {s.total_recovered} | {s.total_failed} | "
            f"{'yes' if s.ever_fatal else 'no'} | {top_journal} ({rate:.0%}) |"
        )
    unused_count = sum(1 for s in stats.values() if s.unused)
    lines += [
        "",
        f"**Used:** {len(used)} rules. **Unused:** {unused_count} rules "
        "(never referenced by any finding in this batch).",
    ]
    return "\n".join(lines)


def _top_journal_rate(stats: BusinessRuleStats) -> tuple[str, float]:
    if not stats.journal_trigger_counts:
        return "—", 0.0
    journal = max(stats.journal_trigger_counts, key=lambda j: stats.trigger_rate_for(j))
    return journal, stats.trigger_rate_for(journal)


def write_business_rule_effectiveness(
    records: tuple[ArticleRecord, ...], output_path: Path
) -> None:
    """Render and write ``Business_Rule_Effectiveness.md`` to disk."""
    output_path.write_text(render_business_rule_effectiveness(records), encoding="utf-8")
