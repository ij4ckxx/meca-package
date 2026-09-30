"""Transformation Summary — Migration Audit / Traceability milestone.

Source -> Extraction -> Transformation -> Generation -> Validation ->
Certification, with each stage's Success/Warnings/Recoveries/Failures.
The engine does not instrument per-stage counters directly — this
module attributes each already-real warning/recovery/finding to a
stage using that finding's own, already-documented provenance (every
:class:`~meca_engine.model.recovery_rules.RecoveryRule`'s description
names the exact module it fires from; every current
:class:`~meca_engine.generators.diagnostics.GeneratorDiagnostic`
originates from a generator, i.e. the Generation stage) — never a new,
invented signal.
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.model.warnings import EngineWarning
    from meca_engine.packaging.conversion_report import ConversionReport

_STAGES = ("Source", "Extraction", "Transformation", "Generation", "Validation", "Certification")

# Each Recovery Rule's own description names the exact module it fires
# from (`model/recovery_rules.py`) — this mapping is read directly off
# that, not guessed:
#   RR-001/002/004: extraction/file_resolver.py
#   RR-005/006: extraction/round_resolver.py
#   RR-003: generators/reviews_xml/review_builder.py
#   RR-007: generators/article_xml/generator.py
_RECOVERY_RULE_STAGE = {
    "RR-001": "Extraction",
    "RR-002": "Extraction",
    "RR-003": "Generation",
    "RR-004": "Extraction",
    "RR-005": "Extraction",
    "RR-006": "Extraction",
    "RR-007": "Generation",
}

_CSS = """
body { font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; }
body { margin: 2rem auto; max-width: 860px; color: #1a1a1a; line-height: 1.5; }
h1 { font-size: 1.5rem; border-bottom: 2px solid #ddd; padding-bottom: 0.5rem; }
h2 { font-size: 1.1rem; margin-top: 2rem; color: #333; }
table { border-collapse: collapse; width: 100%; margin: 0.5rem 0 1rem; }
th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #eee; }
th, td { font-size: 0.92rem; }
th { background: #fafafa; }
.pipeline { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 1rem 0; }
.stage { border: 1px solid #ddd; border-radius: 6px; padding: 0.5rem 0.75rem; }
.stage-arrow { align-self: center; color: #888; }
.note { color: #888; font-size: 0.85rem; font-style: italic; }
"""


def _stage_for_warning(warning: EngineWarning) -> str:
    if warning.recovery_rule_id and warning.recovery_rule_id in _RECOVERY_RULE_STAGE:
        return _RECOVERY_RULE_STAGE[warning.recovery_rule_id]
    return "Generation"


def _build_stage_counts(report: ConversionReport) -> dict[str, dict[str, int]]:
    counts = {stage: {"warnings": 0, "recoveries": 0, "failures": 0} for stage in _STAGES}

    for warning in report.warnings:
        counts[_stage_for_warning(warning)]["warnings"] += 1
    for recovery in report.recoveries:
        counts[_stage_for_warning(recovery)]["recoveries"] += 1
    for diagnostic in report.generator_findings:
        if diagnostic.severity.value == "error":
            counts["Generation"]["failures"] += 1
        elif diagnostic.severity.value == "warning":
            counts["Generation"]["warnings"] += 1

    validation = report.validation_report
    if validation is not None:
        counts["Validation"]["warnings"] += validation.total_warnings
        counts["Validation"]["failures"] += validation.total_errors

    if report.status.value in ("engine_failure", "fatal_failure"):
        counts["Certification"]["failures"] += 1

    return counts


def render_transformation_summary(report: ConversionReport) -> str:
    """Render one package's Transformation Summary as a self-contained HTML string."""
    counts = _build_stage_counts(report)
    pipeline = "".join(
        f'<div class="stage">{escape(stage)}</div>'
        + ('<div class="stage-arrow">&rarr;</div>' if stage != _STAGES[-1] else "")
        for stage in _STAGES
    )

    def _success_label(stage: str) -> str:
        return "No failures/errors recorded" if not counts[stage]["failures"] else "Issues recorded"

    rows = "".join(
        f"<tr><td>{escape(stage)}</td>"
        f"<td>{_success_label(stage)}</td>"
        f"<td>{counts[stage]['warnings']}</td>"
        f"<td>{counts[stage]['recoveries']}</td>"
        f"<td>{counts[stage]['failures']}</td></tr>"
        for stage in _STAGES
    )
    note = (
        '<p class="note">Per-stage attribution is derived from each finding\'s own '
        "documented origin (which module raised it), not a separately-instrumented "
        "per-stage signal — see this module's own docstring.</p>"
    )
    body = (
        f"<h1>Transformation Summary — {escape(report.article_id)}</h1>"
        f'<div class="pipeline">{pipeline}</div>'
        "<h2>Stage Outcomes</h2>"
        "<table><tr><th>Stage</th><th>Success</th><th>Warnings</th>"
        f"<th>Recoveries</th><th>Failures</th></tr>{rows}</table>{note}"
    )
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>Transformation Summary — {escape(report.article_id)}</title>"
        f"<style>{_CSS}</style></head><body>\n{body}\n</body></html>\n"
    )


def write_transformation_summary(report: ConversionReport, output_path: Path) -> None:
    """Render and write one package's Transformation Summary to disk."""
    output_path.write_text(render_transformation_summary(report), encoding="utf-8")
