"""Recovery_Analytics.md and Business_Rule_Statistics.md — Milestone 13.

Management-facing Markdown reports built from
:class:`~meca_engine.reporting.aggregation.MigrationStatistics`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.reporting.aggregation import aggregate

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.packaging.conversion_report import ConversionReport


def render_recovery_analytics(reports: list[ConversionReport]) -> str:
    """Render ``Recovery_Analytics.md`` for a batch of Conversion Reports."""
    stats = aggregate(reports)
    lines = ["# Recovery Analytics", ""]

    lines += ["## Most Common Recovery", ""]
    ranked = sorted(stats.recovery_rule_occurrences.items(), key=lambda item: -item[1])
    if ranked:
        top_rule, top_count = ranked[0]
        lines.append(f"**{top_rule}** — {top_count} occurrences across the batch.")
    else:
        lines.append("No recoveries were applied in this batch.")
    lines.append("")

    lines += ["## Rare Recoveries", ""]
    rare = [(rule, count) for rule, count in ranked if count <= 2]
    if rare:
        for rule, count in rare:
            lines.append(f"- {rule}: {count} occurrence(s)")
    else:
        lines.append("No rarely-used recoveries in this batch.")
    lines.append("")

    lines += ["## Journals Requiring Most Recovery", ""]
    by_journal = sorted(stats.journal_recovery_counts.items(), key=lambda item: -item[1])
    for journal, count in by_journal:
        articles = stats.journal_article_counts.get(journal, 0)
        avg = count / articles if articles else 0
        lines.append(
            f"- {journal}: {count} recoveries across {articles} article(s) (avg {avg:.1f}/article)"
        )
    if not by_journal:
        lines.append("No recoveries were applied in this batch.")
    lines.append("")

    lines += ["## Recovery Trends", ""]
    total_recoveries = sum(stats.recovery_rule_occurrences.values())
    lossless = sum(
        count
        for rule, count in stats.recovery_rule_occurrences.items()
        if rule in ("RR-001", "RR-004", "RR-005")
    )
    lossy = total_recoveries - lossless
    lines.append(f"- Total recoveries applied: {total_recoveries}")
    lines.append(f"- Lossless (derived/matched/deduplicated): {lossless}")
    lines.append(f"- Content-affecting (missing files/metadata): {lossy}")
    lines.append(
        f"- Articles requiring at least one recovery: "
        f"{sum(1 for r in reports if r.recoveries)}/{stats.total_articles}"
    )
    lines.append("")

    return "\n".join(lines)


def write_recovery_analytics(reports: list[ConversionReport], output_path: Path) -> None:
    """Render and write ``Recovery_Analytics.md`` to disk."""
    output_path.write_text(render_recovery_analytics(reports), encoding="utf-8")


def render_business_rule_statistics(reports: list[ConversionReport]) -> str:
    """Render ``Business_Rule_Statistics.md`` for a batch of Conversion Reports."""
    stats = aggregate(reports)
    lines = [
        "# Business Rule Statistics",
        "",
        "For every Business Rule referenced by this batch's findings — Triggered, "
        "Recovered, Warning, and Fatal counts. Rules never referenced by any finding "
        "are omitted from the table below and counted as Unused.",
        "",
        "| Rule | Triggered | Recovered | Warning | Fatal |",
        "|---|---|---|---|---|",
    ]
    used = [u for u in stats.business_rule_usage.values() if not u.unused]
    used.sort(key=lambda u: u.rule_id)
    for usage in used:
        lines.append(
            f"| {usage.rule_id} | {usage.triggered} | {usage.recovered} | "
            f"{usage.warning} | {usage.fatal} |"
        )
    unused_count = sum(1 for u in stats.business_rule_usage.values() if u.unused)
    lines += [
        "",
        f"**Used in this batch:** {len(used)} rules. "
        f"**Unused:** {unused_count} rules (never referenced by any finding).",
    ]
    return "\n".join(lines)


def write_business_rule_statistics(reports: list[ConversionReport], output_path: Path) -> None:
    """Render and write ``Business_Rule_Statistics.md`` to disk."""
    output_path.write_text(render_business_rule_statistics(reports), encoding="utf-8")
