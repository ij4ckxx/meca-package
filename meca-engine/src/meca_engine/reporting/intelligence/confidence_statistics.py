"""Confidence distribution statistics — Milestone 14."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from statistics import median
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.reporting.intelligence.corpus_analyzer import ArticleRecord


@dataclass(frozen=True)
class ConfidenceStats:
    """Corpus-wide confidence score/level distribution."""

    distribution: dict[str, int] = field(default_factory=dict)
    average_score: float = 0.0
    median_score: float = 0.0
    average_by_journal: dict[str, float] = field(default_factory=dict)
    average_by_recovery_rule: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Render as a plain, ``json.dumps``-ready dict."""
        return {
            "distribution": self.distribution,
            "average_score": round(self.average_score, 1),
            "median_score": round(self.median_score, 1),
            "average_by_journal": {k: round(v, 1) for k, v in self.average_by_journal.items()},
            "average_by_recovery_rule": {
                k: round(v, 1) for k, v in self.average_by_recovery_rule.items()
            },
        }


def compute_confidence_statistics(records: tuple[ArticleRecord, ...]) -> ConfidenceStats:
    """Compute :class:`ConfidenceStats` for a batch of articles."""
    if not records:
        return ConfidenceStats()

    scores = [r.confidence_score for r in records]
    distribution: Counter[str] = Counter(r.overall_confidence for r in records)

    by_journal: dict[str, list[int]] = {}
    for record in records:
        by_journal.setdefault(record.journal, []).append(record.confidence_score)

    by_rule: dict[str, list[int]] = {}
    for record in records:
        for rule_id in record.recovery_rules_triggered:
            by_rule.setdefault(rule_id, []).append(record.confidence_score)

    return ConfidenceStats(
        distribution=dict(distribution),
        average_score=sum(scores) / len(scores),
        median_score=float(median(scores)),
        average_by_journal={j: sum(v) / len(v) for j, v in by_journal.items()},
        average_by_recovery_rule={r: sum(v) / len(v) for r, v in by_rule.items()},
    )


def render_confidence_analysis(records: tuple[ArticleRecord, ...]) -> str:
    """Render ``Confidence_Analysis.md`` for a batch of articles."""
    stats = compute_confidence_statistics(records)
    lines = [
        "# Confidence Analysis",
        "",
        f"- Average confidence score: {stats.average_score:.1f}/100",
        f"- Median confidence score: {stats.median_score:.1f}/100",
        "",
        "## Distribution",
        "",
        "| Level | Articles |",
        "|---|---|",
    ]
    for level, count in sorted(stats.distribution.items()):
        lines.append(f"| {level.upper()} | {count} |")

    lines += ["", "## Average Confidence by Journal", "", "| Journal | Avg Score |", "|---|---|"]
    for journal, avg in sorted(stats.average_by_journal.items(), key=lambda item: item[1]):
        lines.append(f"| {journal} | {avg:.1f} |")

    lines += [
        "",
        "## Average Confidence by Recovery Rule",
        "",
        "| Recovery Rule | Avg Article Confidence |",
        "|---|---|",
    ]
    for rule_id, avg in sorted(stats.average_by_recovery_rule.items()):
        lines.append(f"| {rule_id} | {avg:.1f} |")

    return "\n".join(lines)


def write_confidence_analysis(records: tuple[ArticleRecord, ...], output_path: Path) -> None:
    """Render and write ``Confidence_Analysis.md`` to disk."""
    output_path.write_text(render_confidence_analysis(records), encoding="utf-8")
