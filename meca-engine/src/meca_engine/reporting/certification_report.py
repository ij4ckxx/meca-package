"""Per-article Certification Report — Milestone 13.

Renders a single :class:`~meca_engine.packaging.conversion_report.ConversionReport`
as a self-contained, human-readable HTML page for production/archival
staff — plain semantic HTML with inline styling, no JavaScript, no
external assets, no Python tracebacks or internal object dumps.
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.packaging.conversion_report import ConversionReport

_STATUS_LABELS = {
    "certified": "Certified",
    "certified_with_warnings": "Certified — with warnings",
    "certified_with_recovery": "Certified — with recovery",
    "partial_certification": "Partially certified",
    "engine_failure": "Not generated — engine failure",
    "fatal_failure": "Not generated — fatal source-data failure",
}

_STATUS_EXPLANATION = {
    "certified": (
        "The package was generated exactly as declared in the source archive, "
        "with no recovery needed."
    ),
    "certified_with_warnings": (
        "The package was generated successfully. Some information was incomplete or a "
        "Business Rule was not fully satisfied, but nothing was altered to produce this package."
    ),
    "certified_with_recovery": (
        "The package was generated successfully. The engine applied one or more "
        "deterministic Recovery Rules to work around historical defects in the source "
        "data, without inventing any information."
    ),
    "partial_certification": (
        "The package was generated, but at least one declared file could not be located "
        "and is absent from the package. Everything else generated normally."
    ),
    "engine_failure": (
        "The package could not be generated because of a defect or gap in the engine "
        "itself, not the submitted archive."
    ),
    "fatal_failure": (
        "The package could not be generated because the source data made safe "
        "generation impossible (e.g. unreadable XML, no manuscript file)."
    ),
}

_CSS = """
body { font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; }
body { margin: 2rem auto; max-width: 860px; color: #1a1a1a; line-height: 1.5; }
h1 { font-size: 1.5rem; border-bottom: 2px solid #ddd; padding-bottom: 0.5rem; }
h2 { font-size: 1.1rem; margin-top: 2rem; color: #333; }
.badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 999px; }
.badge { font-weight: 600; font-size: 0.9rem; }
.badge-good { background: #e6f4ea; color: #1e7e34; }
.badge-warn { background: #fff8e1; color: #8a6d00; }
.badge-bad { background: #fdecea; color: #b3261e; }
table { border-collapse: collapse; width: 100%; margin: 0.5rem 0 1rem; }
th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #eee; }
th, td { font-size: 0.92rem; }
th { background: #fafafa; }
.meta { color: #555; font-size: 0.95rem; }
.empty { color: #888; font-style: italic; }
ul { margin: 0.25rem 0; }
"""

_BADGE_CLASS = {
    "certified": "badge-good",
    "certified_with_warnings": "badge-good",
    "certified_with_recovery": "badge-good",
    "partial_certification": "badge-warn",
    "engine_failure": "badge-bad",
    "fatal_failure": "badge-bad",
}


def render_certification_report(report: ConversionReport) -> str:
    """Render one article's Certification Report as a self-contained HTML string."""
    status_value = report.status.value
    sections = [
        _header(report, status_value),
        _failure_reason(report),
        _summary_table(report, status_value),
        _recovery_summary(report),
        _warning_summary(report),
        _missing_information(report),
        _generated_files(report),
        _business_rules_section(report),
        _recovery_rules_section(report),
        _manual_review_section(report),
    ]
    body = "\n".join(sections)
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>Certification Report — {escape(report.article_id)}</title>"
        f"<style>{_CSS}</style></head><body>\n{body}\n</body></html>\n"
    )


def write_certification_report(report: ConversionReport, output_path: Path) -> None:
    """Render and write one article's Certification Report to disk."""
    output_path.write_text(render_certification_report(report), encoding="utf-8")


def _header(report: ConversionReport, status_value: str) -> str:
    badge_class = _BADGE_CLASS.get(status_value, "badge-warn")
    label = _STATUS_LABELS.get(status_value, status_value)
    return (
        f"<h1>Certification Report — {escape(report.article_id)}</h1>"
        f'<p><span class="badge {badge_class}">{escape(label)}</span></p>'
        f'<p class="meta">{escape(_STATUS_EXPLANATION.get(status_value, ""))}</p>'
    )


def _failure_reason(report: ConversionReport) -> str:
    """The specific reason generation didn't complete, when there is one.

    ``_STATUS_EXPLANATION`` above is a generic, per-status template
    sentence — for an ``engine_failure``/``fatal_failure`` article, the
    real, specific reason (e.g. "No source XML found for ... under ...")
    already exists on ``report.unrecoverable_error`` but was previously
    never shown in this, the first report an operator opens for a failed
    article (see `Operator_Guide.md`).
    """
    error = report.unrecoverable_error
    if error is None:
        return ""
    detail = f"Stage: {escape(error.stage)}"
    if error.rule_id:
        detail += f" · Rule: {escape(error.rule_id)}"
    return f'<h2>Failure Reason</h2><p>{escape(error.message)}</p><p class="meta">{detail}</p>'


def _summary_table(report: ConversionReport, status_value: str) -> str:
    rows = [
        ("Article ID", report.article_id),
        ("Journal", report.journal or "—"),
        ("Status", _STATUS_LABELS.get(status_value, status_value)),
        ("Overall Confidence", report.overall_confidence.value.upper()),
        ("Confidence Score", f"{report.confidence_score}/100"),
    ]
    row_html = "".join(f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>" for k, v in rows)
    return f"<h2>Overview</h2><table>{row_html}</table>"


def _recovery_summary(report: ConversionReport) -> str:
    if not report.recoveries:
        return '<h2>Recovery Summary</h2><p class="empty">No recovery was needed.</p>'
    items = "".join(
        f"<li>{escape(r.message)}"
        + (f" <em>(file: {escape(r.affected_file)})</em>" if r.affected_file else "")
        + "</li>"
        for r in report.recoveries
    )
    return f"<h2>Recovery Summary ({len(report.recoveries)})</h2><ul>{items}</ul>"


def _warning_summary(report: ConversionReport) -> str:
    advisory_count = len(report.warnings) + len(report.generator_findings)
    if advisory_count == 0:
        return '<h2>Warning Summary</h2><p class="empty">No warnings.</p>'
    items = "".join(f"<li>{escape(w.message)}</li>" for w in report.warnings)
    items += "".join(f"<li>{escape(f.message)}</li>" for f in report.generator_findings)
    return f"<h2>Warning Summary ({advisory_count})</h2><ul>{items}</ul>"


def _missing_information(report: ConversionReport) -> str:
    if not report.missing_files and not report.missing_metadata:
        return (
            '<h2>Missing Information</h2><p class="empty">Nothing is missing from this package.</p>'
        )
    parts = ["<h2>Missing Information</h2>"]
    if report.missing_files:
        items = "".join(f"<li>{escape(f)}</li>" for f in report.missing_files)
        parts.append(
            f"<p>Files that could not be located in the source archive:</p><ul>{items}</ul>"
        )
    if report.missing_metadata:
        items = "".join(f"<li>{escape(m)}</li>" for m in report.missing_metadata)
        parts.append(f"<p>Metadata that could not be determined:</p><ul>{items}</ul>")
    return "".join(parts)


def _generated_files(report: ConversionReport) -> str:
    if not report.generated_files:
        return '<h2>Generated Files</h2><p class="empty">No physical files were packaged.</p>'
    items = "".join(f"<li>{escape(f)}</li>" for f in report.generated_files)
    return f"<h2>Generated Files ({len(report.generated_files)})</h2><ul>{items}</ul>"


def _business_rules_section(report: ConversionReport) -> str:
    if not report.business_rules_failed and not report.business_rule_findings:
        return (
            "<h2>Business Rules Affected</h2>"
            '<p class="empty">No Business Rule deviations observed.</p>'
        )
    items = "".join(
        f"<li>{escape(f.rule_id)} — {escape(f.message)}</li>" for f in report.business_rule_findings
    )
    return f"<h2>Business Rules Affected</h2><ul>{items}</ul>"


def _recovery_rules_section(report: ConversionReport) -> str:
    if not report.recovery_rules_applied:
        return '<h2>Recovery Rules Applied</h2><p class="empty">None.</p>'
    items = "".join(f"<li>{escape(rid)}</li>" for rid in report.recovery_rules_applied)
    return f"<h2>Recovery Rules Applied</h2><ul>{items}</ul>"


def _manual_review_section(report: ConversionReport) -> str:
    reasons = _manual_review_reasons(report)
    if not reasons:
        return (
            "<h2>Manual Review Recommendations</h2>"
            '<p class="empty">No manual review is recommended for this package.</p>'
        )
    items = "".join(f"<li>{escape(r)}</li>" for r in reasons)
    return f"<h2>Manual Review Recommendations</h2><ul>{items}</ul>"


def _manual_review_reasons(report: ConversionReport) -> list[str]:
    reasons: list[str] = []
    if report.missing_files:
        reasons.append(
            "Confirm the missing file(s) were not required for archival completeness, or source "
            "them from an alternate copy if available."
        )
    if any(w.confidence.value == "low" for w in report.recoveries):
        reasons.append(
            "Spot-check the low-confidence file matches to confirm they resolved to the "
            "correct file."
        )
    if report.status.value == "partial_certification":
        reasons.append(
            "This package is missing declared content — review before archival sign-off."
        )
    return reasons
