"""Cross-article aggregation — Milestone 13 (Archive Migration Certification & Reporting).

Computes corpus-level statistics from a batch of
:class:`~meca_engine.packaging.conversion_report.ConversionReport`
instances. Every other reporting module (`migration_summary`,
`recovery_analytics`, `business_rule_statistics`, `dashboard`) is built
on top of this one aggregation pass, so the numbers are always
consistent across reports. Pure computation — no file I/O, no new
engine/business logic, reads only what `ConversionReport` already
exposes.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meca_engine.packaging.conversion_report import ConversionReport

# The Business Rule Book is numbered BR-001..BR-160 (confirmed sequential,
# no gaps, per the prior production-validation audit) — used so a rule
# that is never referenced by any finding still shows up as "unused"
# rather than being silently absent from the statistics.
ALL_BUSINESS_RULE_IDS: tuple[str, ...] = tuple(f"BR-{i:03d}" for i in range(1, 161))


@dataclass(frozen=True)
class BusinessRuleUsage:
    """One Business Rule's observed usage across a batch."""

    rule_id: str
    triggered: int
    recovered: int
    warning: int
    fatal: int

    @property
    def unused(self) -> bool:
        """Whether this rule was never referenced by any finding in the batch."""
        return self.triggered == 0


@dataclass(frozen=True)
class MigrationStatistics:
    """Corpus-level statistics computed from a batch of Conversion Reports."""

    total_articles: int
    status_counts: dict[str, int] = field(default_factory=dict)
    confidence_distribution: dict[str, int] = field(default_factory=dict)
    recovery_rule_occurrences: dict[str, int] = field(default_factory=dict)
    business_rule_usage: dict[str, BusinessRuleUsage] = field(default_factory=dict)
    journal_article_counts: dict[str, int] = field(default_factory=dict)
    journal_recovery_counts: dict[str, int] = field(default_factory=dict)
    failure_reason_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class _BusinessRuleCounters:
    triggered: Counter[str] = field(default_factory=Counter)
    recovered: Counter[str] = field(default_factory=Counter)
    warning: Counter[str] = field(default_factory=Counter)
    fatal: Counter[str] = field(default_factory=Counter)


def _accumulate_engine_warnings(
    report: ConversionReport,
    counters: _BusinessRuleCounters,
    recovery_rule_occurrences: Counter[str],
) -> None:
    for recovery in report.recoveries:
        if recovery.recovery_rule_id:
            recovery_rule_occurrences[recovery.recovery_rule_id] += 1
        if recovery.rule_id:
            counters.triggered[recovery.rule_id] += 1
            counters.recovered[recovery.rule_id] += 1

    for advisory in report.warnings:
        if advisory.rule_id:
            counters.triggered[advisory.rule_id] += 1
            counters.warning[advisory.rule_id] += 1


def _accumulate_generator_findings(
    report: ConversionReport,
    counters: _BusinessRuleCounters,
    recovery_rule_occurrences: Counter[str],
) -> None:
    for finding in report.generator_findings:
        business_rule_id = _business_rule_id_in(finding.message)
        if business_rule_id:
            counters.triggered[business_rule_id] += 1
            if finding.severity.value == "error":
                counters.fatal[business_rule_id] += 1
            else:
                counters.warning[business_rule_id] += 1
        recovery_rule_id = _recovery_rule_id_in(finding.message)
        if recovery_rule_id:
            recovery_rule_occurrences[recovery_rule_id] += 1


def _accumulate_business_rule_counts(
    report: ConversionReport,
    counters: _BusinessRuleCounters,
    recovery_rule_occurrences: Counter[str],
) -> None:
    _accumulate_engine_warnings(report, counters, recovery_rule_occurrences)
    _accumulate_generator_findings(report, counters, recovery_rule_occurrences)
    for fatal_error in report.fatal_errors:
        if fatal_error.rule_id:
            counters.triggered[fatal_error.rule_id] += 1
            counters.fatal[fatal_error.rule_id] += 1


def aggregate(reports: list[ConversionReport]) -> MigrationStatistics:
    """Compute :class:`MigrationStatistics` from a list of Conversion Reports."""
    status_counts: Counter[str] = Counter()
    confidence_distribution: Counter[str] = Counter()
    recovery_rule_occurrences: Counter[str] = Counter()
    journal_article_counts: Counter[str] = Counter()
    journal_recovery_counts: Counter[str] = Counter()
    failure_reason_counts: Counter[str] = Counter()
    counters = _BusinessRuleCounters()

    for report in reports:
        journal = report.journal or "Unknown"
        status_counts[report.status.value] += 1
        confidence_distribution[report.overall_confidence.value] += 1
        journal_article_counts[journal] += 1
        journal_recovery_counts[journal] += len(report.recoveries)
        for fatal_error in report.fatal_errors:
            failure_reason_counts[fatal_error.error_type] += 1
        _accumulate_business_rule_counts(report, counters, recovery_rule_occurrences)

    business_rule_usage = {
        rule_id: BusinessRuleUsage(
            rule_id=rule_id,
            triggered=counters.triggered[rule_id],
            recovered=counters.recovered[rule_id],
            warning=counters.warning[rule_id],
            fatal=counters.fatal[rule_id],
        )
        for rule_id in ALL_BUSINESS_RULE_IDS
    }

    return MigrationStatistics(
        total_articles=len(reports),
        status_counts=dict(status_counts),
        confidence_distribution=dict(confidence_distribution),
        recovery_rule_occurrences=dict(recovery_rule_occurrences),
        business_rule_usage=business_rule_usage,
        journal_article_counts=dict(journal_article_counts),
        journal_recovery_counts=dict(journal_recovery_counts),
        failure_reason_counts=dict(failure_reason_counts),
    )


def _business_rule_id_in(message: str) -> str | None:
    match = re.search(r"BR-\d+", message)
    return match.group(0) if match else None


def _recovery_rule_id_in(message: str) -> str | None:
    match = re.search(r"RR-\d+", message)
    return match.group(0) if match else None
