"""Conversion Report — Milestone 12 (Archive Migration Engine).

A JSON-ready summary of one article's conversion attempt, covering both a
successful build (:class:`~meca_engine.packaging.models.StagedPackage`)
and a failed one (a raised :class:`~meca_engine.exceptions.base.MecaEngineError`).
Deliberately a plain, standalone dataclass built by whichever caller
already orchestrates one article's conversion (e.g. a batch runner) —
no new orchestration layer, no change to :class:`~meca_engine.packaging.builder.PackageBuilder`
beyond what it already returns. This module only reads existing outputs
and reshapes them; it introduces no new business logic.

Not a dashboard: this module produces the report *model* only, per this
milestone's explicit scope.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from meca_engine.model.recovery_rules import SIGNIFICANT_DEFICIENCY_RULE_IDS
from meca_engine.model.warnings import ConfidenceLevel
from meca_engine.packaging.models import PackageStatus

if TYPE_CHECKING:
    from meca_engine.exceptions.base import MecaEngineError
    from meca_engine.generators.diagnostics import GeneratorDiagnostic
    from meca_engine.model.warnings import EngineWarning
    from meca_engine.packaging.models import StagedPackage
    from meca_engine.reporting.reproducibility import ReproducibilityInfo
    from meca_engine.validation.models import PackageValidationReport

_BUSINESS_RULE_ID_PATTERN = re.compile(r"BR-\d+")
_RECOVERY_RULE_ID_PATTERN = re.compile(r"RR-\d+")

# The Business Rules this milestone's recovery framework has explicit,
# per-article pass/fail signal for (whether a warning/recovery fired
# against them) — used for `ConversionReport.business_rules_passed`/
# `business_rules_failed`. The full 160-rule catalog is not re-validated
# per package here; see `production_validation/` for corpus-level
# statistics across all of them.
_TRACKED_BUSINESS_RULE_IDS: tuple[str, ...] = (
    "BR-010",
    "BR-011",
    "BR-013",
    "BR-016",
    "BR-063",
    "BR-112",
)

# Recovery Rules that omit *metadata* (identity, round attribution, an
# optional XML section) rather than lose a physical file. Distinct from
# `SIGNIFICANT_DEFICIENCY_RULE_IDS` (RR-002 — a missing file), which is a
# strictly bigger deficiency than a metadata omission.
_MISSING_METADATA_RULE_IDS: frozenset[str] = frozenset({"RR-003", "RR-006", "RR-007"})

# Confidence-score weights (Milestone 13: formalized, see
# `_confidence_score`'s docstring for the calculation this implements).
# Deliberately simple and documented rather than tuned: this is an
# advisory signal for triage, not a certification verdict
# (:class:`PackageStatus` remains the authoritative outcome).
_LOSSLESS_RECOVERY_PENALTY = 2  # successful recovery, nothing lost (RR-001/004/005)
_MISSING_METADATA_PENALTY = 5  # metadata omitted, not fabricated (RR-003/006/007)
_SKIPPED_ASSET_PENALTY = 12  # a declared file is absent from the package (RR-002)
_UNRESOLVED_WARNING_PENALTY = 3  # an advisory finding with no recovery at all
_FATAL_DEFICIENCY_PENALTY = 8  # a generator-layer ERROR-severity observation

# Bucketing thresholds for `overall_confidence` — reporting-only.
_HIGH_CONFIDENCE_THRESHOLD = 70
_MEDIUM_CONFIDENCE_THRESHOLD = 40


@dataclass(frozen=True)
class BusinessRuleFinding:
    """One Business-Rule-tagged observation surfaced during conversion.

    Sourced from either an :class:`EngineWarning` with a ``rule_id``, or
    a :class:`GeneratorDiagnostic` whose message text names a rule (e.g.
    "...BR-103's recommendation review-item is not emitted...") —
    ``GeneratorDiagnostic`` has no structured rule-id field of its own
    (Milestone 6A design; not changed here), so this is a message-text
    extraction for that source, not a schema guarantee.
    """

    rule_id: str
    message: str
    severity: str
    source: str  # "engine_warning" | "generator_diagnostic"

    def to_dict(self) -> dict[str, Any]:
        """Render as a plain, ``json.dumps``-ready dict."""
        return {
            "rule_id": self.rule_id,
            "message": self.message,
            "severity": self.severity,
            "source": self.source,
        }


@dataclass(frozen=True)
class UnrecoverableError:
    """One fatal condition that stopped generation entirely."""

    error_type: str
    message: str
    stage: str
    rule_id: str | None
    article_id: str | None

    def to_dict(self) -> dict[str, Any]:
        """Render as a plain, ``json.dumps``-ready dict."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "stage": self.stage,
            "rule_id": self.rule_id,
            "article_id": self.article_id,
        }


@dataclass(frozen=True)
class ConversionReport:
    """A JSON-ready summary of one article's conversion attempt.

    Attributes:
        article_id: The article this report covers.
        status: The final :class:`~meca_engine.packaging.models.PackageStatus`.
        confidence_score: 0-100 advisory signal — see module-level
            penalty weights. Always 0 when ``unrecoverable_error`` is set.
        overall_confidence: The same signal, bucketed into
            :class:`~meca_engine.model.warnings.ConfidenceLevel` for
            reporting.
        warnings: Advisory :class:`EngineWarning` entries
            (``is_recovery=False``) — nothing was changed to produce
            these, they are worth reviewing.
        recoveries: :class:`EngineWarning` entries where the engine
            actually altered, omitted, or derived something
            (``is_recovery=True``).
        generator_findings: Every :class:`GeneratorDiagnostic` recorded
            during generation (a separate, pre-existing diagnostic
            system — see ``model/warnings.py``'s module docstring for
            why it is not merged into ``warnings``/``recoveries``).
        unrecoverable_error: Set only when ``status`` is
            ``ENGINE_FAILURE``/``FATAL_FAILURE`` — the exception that
            stopped generation.
        fatal_errors: The same information as ``unrecoverable_error``,
            in list form (empty, or a single entry) — provided under
            this name to match the Conversion Report's plural field
            convention (``warnings``, ``recoveries``, ...).
        business_rule_findings: Every observation, from either source
            above, that names a specific Business Rule.
        business_rules_passed: Of `_TRACKED_BUSINESS_RULE_IDS`, the ones
            with no warning/recovery/diagnostic against them for this
            article.
        business_rules_failed: Of `_TRACKED_BUSINESS_RULE_IDS`, the ones
            with at least one warning/recovery/diagnostic against them.
        recovery_rules_applied: The distinct Recovery Rule IDs
            (`model/recovery_rules.py`) that fired for this article.
        generated_files: Every physical file actually packaged.
        missing_files: Declared files that could not be resolved (Recovery
            Rule RR-002) — same underlying event as ``skipped_files``.
        skipped_files: Alias of ``missing_files``, provided under both
            names since "missing" and "skipped" are the same event in
            this engine (a file is skipped *because* it is missing).
        missing_metadata: Human-readable descriptions of metadata (not a
            whole file) the engine had to omit rather than fabricate —
            e.g. a reviewer's identity, or a round's attribution
            (Recovery Rules RR-003/006/007).
        journal: The journal this article belongs to (display name),
            for reporting/grouping. Empty string if not supplied by the
            caller.
        validation_report: DTD/well-formedness validation findings for
            this package's 4 generated XML documents.
        reproducibility: What produced this package and the facts
            needed to reproduce it later (Migration Audit milestone) —
            ``None`` for any report built before that milestone.
    """

    article_id: str
    status: PackageStatus
    confidence_score: int
    overall_confidence: ConfidenceLevel = ConfidenceLevel.LOW
    warnings: tuple[EngineWarning, ...] = field(default_factory=tuple)
    recoveries: tuple[EngineWarning, ...] = field(default_factory=tuple)
    generator_findings: tuple[GeneratorDiagnostic, ...] = field(default_factory=tuple)
    unrecoverable_error: UnrecoverableError | None = None
    fatal_errors: tuple[UnrecoverableError, ...] = field(default_factory=tuple)
    business_rule_findings: tuple[BusinessRuleFinding, ...] = field(default_factory=tuple)
    business_rules_passed: tuple[str, ...] = field(default_factory=tuple)
    business_rules_failed: tuple[str, ...] = field(default_factory=tuple)
    recovery_rules_applied: tuple[str, ...] = field(default_factory=tuple)
    generated_files: tuple[str, ...] = field(default_factory=tuple)
    missing_files: tuple[str, ...] = field(default_factory=tuple)
    skipped_files: tuple[str, ...] = field(default_factory=tuple)
    missing_metadata: tuple[str, ...] = field(default_factory=tuple)
    journal: str = ""
    validation_report: PackageValidationReport | None = None
    reproducibility: ReproducibilityInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        """Render as a plain, ``json.dumps``-ready dict."""
        return {
            "article_id": self.article_id,
            "status": self.status.value,
            "confidence_score": self.confidence_score,
            "overall_confidence": self.overall_confidence.value,
            "warnings": [_warning_to_dict(w) for w in self.warnings],
            "recoveries": [_warning_to_dict(w) for w in self.recoveries],
            "generator_findings": [_diagnostic_to_dict(d) for d in self.generator_findings],
            "unrecoverable_error": (
                self.unrecoverable_error.to_dict() if self.unrecoverable_error else None
            ),
            "fatal_errors": [e.to_dict() for e in self.fatal_errors],
            "business_rule_findings": [f.to_dict() for f in self.business_rule_findings],
            "business_rules_passed": list(self.business_rules_passed),
            "business_rules_failed": list(self.business_rules_failed),
            "recovery_rules_applied": list(self.recovery_rules_applied),
            "generated_files": list(self.generated_files),
            "missing_files": list(self.missing_files),
            "skipped_files": list(self.skipped_files),
            "missing_metadata": list(self.missing_metadata),
            "journal": self.journal,
            "validation_report": (
                self.validation_report.to_dict() if self.validation_report else None
            ),
            "reproducibility": (self.reproducibility.to_dict() if self.reproducibility else None),
        }


def build_conversion_report(
    article_id: str,
    *,
    staged_package: StagedPackage | None = None,
    error: MecaEngineError | None = None,
    failed_status: PackageStatus = PackageStatus.FATAL_FAILURE,
    journal: str = "",
) -> ConversionReport:
    """Build a :class:`ConversionReport` from a successful or failed conversion.

    Args:
        article_id: The article this report covers.
        staged_package: The successful build result, if generation
            completed (mutually exclusive with ``error``).
        error: The exception that stopped generation, if it did not
            complete (mutually exclusive with ``staged_package``).
        failed_status: Which failure status to record when ``error`` is
            given — the caller decides ``ENGINE_FAILURE`` vs
            ``FATAL_FAILURE`` (see ``02_Recovery_Matrix.md`` for the
            classification assigned to every reachable exception site);
            defaults to ``FATAL_FAILURE``.
        journal: The journal this article belongs to, for reporting —
            the caller already knows this (see the batch script); not
            re-derived here to avoid adding a new dependency.
    """
    if staged_package is not None:
        warnings = tuple(w for w in staged_package.warnings if not w.is_recovery)
        recoveries = tuple(w for w in staged_package.warnings if w.is_recovery)
        generator_findings = staged_package.generator_diagnostics
        confidence = _confidence_score(warnings, recoveries, generator_findings)
        triggered_rule_ids = {
            w.rule_id for w in staged_package.warnings if w.rule_id
        } | _extract_rule_ids(generator_findings, _BUSINESS_RULE_ID_PATTERN)
        missing_files = tuple(
            w.affected_file
            for w in recoveries
            if w.recovery_rule_id in SIGNIFICANT_DEFICIENCY_RULE_IDS and w.affected_file
        )
        missing_metadata = tuple(
            w.message for w in recoveries if w.recovery_rule_id in _MISSING_METADATA_RULE_IDS
        )
        return ConversionReport(
            article_id=article_id,
            status=staged_package.status,
            confidence_score=confidence,
            overall_confidence=_confidence_level(confidence),
            warnings=warnings,
            recoveries=recoveries,
            generator_findings=generator_findings,
            business_rule_findings=_extract_business_rule_findings(
                staged_package.warnings, generator_findings
            ),
            business_rules_passed=tuple(
                rid for rid in _TRACKED_BUSINESS_RULE_IDS if rid not in triggered_rule_ids
            ),
            business_rules_failed=tuple(
                rid for rid in _TRACKED_BUSINESS_RULE_IDS if rid in triggered_rule_ids
            ),
            recovery_rules_applied=_extract_recovery_rule_ids(recoveries, generator_findings),
            generated_files=tuple(f.href for f in staged_package.packaged_files),
            missing_files=missing_files,
            skipped_files=missing_files,
            missing_metadata=missing_metadata,
            journal=journal,
        )

    if error is not None:
        unrecoverable = UnrecoverableError(
            error_type=type(error).__name__,
            message=error.message,
            stage=error.stage,
            rule_id=error.rule_id,
            article_id=article_id,
        )
        findings = (
            (
                BusinessRuleFinding(
                    rule_id=error.rule_id,
                    message=error.message,
                    severity="error",
                    source="engine_warning",
                ),
            )
            if error.rule_id
            else ()
        )
        return ConversionReport(
            article_id=article_id,
            status=failed_status,
            confidence_score=0,
            overall_confidence=ConfidenceLevel.LOW,
            unrecoverable_error=unrecoverable,
            fatal_errors=(unrecoverable,),
            business_rule_findings=findings,
            business_rules_failed=(error.rule_id,) if error.rule_id else (),
            journal=journal,
        )

    raise ValueError("build_conversion_report requires either staged_package or error")


def _confidence_score(
    warnings: tuple[EngineWarning, ...],
    recoveries: tuple[EngineWarning, ...],
    generator_findings: tuple[GeneratorDiagnostic, ...],
) -> int:
    """Formalized confidence calculation (Milestone 13).

    Starts at 100 and subtracts one weighted penalty per finding, in five
    categories — each a distinct, documented dimension of "how much did
    the engine have to compensate, and how much is genuinely missing":

    1. **Successful (lossless) recovery** — a Recovery Rule fired but no
       declared content was lost (RR-001/004/005: filename derived,
       tolerant match, round dedup). Smallest penalty.
    2. **Missing metadata** — a Recovery Rule omitted metadata rather
       than a whole file (RR-003/006/007: reviewer identity, round
       attribution, an optional XML section). Moderate penalty.
    3. **Skipped asset** — a declared file could not be resolved and is
       absent from the package (RR-002). The largest per-instance
       penalty: real content is missing, not just re-derived.
    4. **Unresolved warning** — an advisory finding with no recovery at
       all (an ``EngineWarning`` with ``is_recovery=False``, or a
       generator-layer INFO/WARNING diagnostic).
    5. **Fatal-adjacent deficiency** — a generator-layer ERROR-severity
       diagnostic: generation still completed, but this is the
       strongest non-fatal signal something is more seriously wrong.

    A package that did not generate at all (``ENGINE_FAILURE``/
    ``FATAL_FAILURE``) never reaches this function — its score is fixed
    at 0 in :func:`build_conversion_report`.
    """
    score = 100
    for recovery in recoveries:
        if recovery.recovery_rule_id in SIGNIFICANT_DEFICIENCY_RULE_IDS:
            score -= _SKIPPED_ASSET_PENALTY
        elif recovery.recovery_rule_id in _MISSING_METADATA_RULE_IDS:
            score -= _MISSING_METADATA_PENALTY
        else:
            score -= _LOSSLESS_RECOVERY_PENALTY
    score -= _UNRESOLVED_WARNING_PENALTY * len(warnings)
    for finding in generator_findings:
        severity = finding.severity.value
        if severity == "error":
            score -= _FATAL_DEFICIENCY_PENALTY
        elif severity == "warning":
            score -= _UNRESOLVED_WARNING_PENALTY
        # "info"-severity generator findings are purely informational —
        # no penalty (e.g. "no file-manifest entries for the latest round").
    return max(score, 0)


def _confidence_level(score: int) -> ConfidenceLevel:
    if score >= _HIGH_CONFIDENCE_THRESHOLD:
        return ConfidenceLevel.HIGH
    if score >= _MEDIUM_CONFIDENCE_THRESHOLD:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def _extract_rule_ids(
    generator_findings: tuple[GeneratorDiagnostic, ...], pattern: re.Pattern[str]
) -> set[str]:
    return {
        match.group(0)
        for diagnostic in generator_findings
        for match in pattern.finditer(diagnostic.message)
    }


def _extract_recovery_rule_ids(
    recoveries: tuple[EngineWarning, ...],
    generator_findings: tuple[GeneratorDiagnostic, ...],
) -> tuple[str, ...]:
    from_warnings = {w.recovery_rule_id for w in recoveries if w.recovery_rule_id}
    from_diagnostics = _extract_rule_ids(generator_findings, _RECOVERY_RULE_ID_PATTERN)
    return tuple(sorted(from_warnings | from_diagnostics))


def _extract_business_rule_findings(
    warnings: tuple[EngineWarning, ...],
    generator_findings: tuple[GeneratorDiagnostic, ...],
) -> tuple[BusinessRuleFinding, ...]:
    findings: list[BusinessRuleFinding] = []
    for warning in warnings:
        if warning.rule_id:
            findings.append(
                BusinessRuleFinding(
                    rule_id=warning.rule_id,
                    message=warning.message,
                    severity=warning.severity.value,
                    source="engine_warning",
                )
            )
    for diagnostic in generator_findings:
        match = _BUSINESS_RULE_ID_PATTERN.search(diagnostic.message)
        if match:
            findings.append(
                BusinessRuleFinding(
                    rule_id=match.group(0),
                    message=diagnostic.message,
                    severity=diagnostic.severity.value,
                    source="generator_diagnostic",
                )
            )
    return tuple(findings)


def _warning_to_dict(warning: EngineWarning) -> dict[str, Any]:
    return {
        "code": warning.code,
        "rule": warning.recovery_rule_id or warning.rule_id,
        "business_rule_id": warning.rule_id,
        "recovery_rule_id": warning.recovery_rule_id,
        "category": warning.category.value,
        "severity": warning.severity.value,
        "origin": warning.origin.value,
        "recovery_applied": warning.is_recovery,
        "confidence": warning.confidence.value,
        "message": warning.message,
        "affected_file": warning.affected_file,
        "affected_article": warning.article_id,
        "suggested_action": warning.suggested_action,
        "context": warning.context_dict(),
    }


def _diagnostic_to_dict(diagnostic: GeneratorDiagnostic) -> dict[str, Any]:
    business_rule_match = _BUSINESS_RULE_ID_PATTERN.search(diagnostic.message)
    recovery_rule_match = _RECOVERY_RULE_ID_PATTERN.search(diagnostic.message)
    return {
        "severity": diagnostic.severity.value,
        "generator_name": diagnostic.generator_name,
        "message": diagnostic.message,
        "business_rule_id": business_rule_match.group(0) if business_rule_match else None,
        "recovery_rule_id": recovery_rule_match.group(0) if recovery_rule_match else None,
        "context": dict(diagnostic.context),
    }
