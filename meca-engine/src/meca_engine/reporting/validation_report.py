"""Standalone per-package XML Validation Report — Milestone 2.

Renders a single :class:`~meca_engine.validation.models.PackageValidationReport`
as a self-contained HTML page, matching
:mod:`meca_engine.reporting.certification_report`'s own style and
conventions (plain semantic HTML, inline styling, no JavaScript).
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.validation.models import FileValidationReport, PackageValidationReport

_BADGE_CLASS = {
    "pass": "badge-good",
    "warning": "badge-warn",
    "error": "badge-bad",
}

_CATEGORY_LABELS = {
    "source_data_issue": "Source Data Issue",
    "business_rule_candidate": "Business Rule Candidate",
    "recovery_rule_candidate": "Recovery Rule Candidate",
    "validation_only": "Validation Only",
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


def render_validation_report(report: PackageValidationReport) -> str:
    """Render one package's XML Validation Report as a self-contained HTML string."""
    sections = [_header(report), _summary_table(report), _category_summary(report)]
    sections.extend(_file_section(f) for f in report.files)
    body = "\n".join(sections)
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>Validation Report — {escape(report.article_id)}</title>"
        f"<style>{_CSS}</style></head><body>\n{body}\n</body></html>\n"
    )


def write_validation_report(report: PackageValidationReport, output_path: Path) -> None:
    """Render and write one package's XML Validation Report to disk."""
    output_path.write_text(render_validation_report(report), encoding="utf-8")


def _header(report: PackageValidationReport) -> str:
    overall = report.overall_result.value
    badge_class = _BADGE_CLASS.get(overall, "badge-warn")
    return (
        f"<h1>XML Validation Report — {escape(report.article_id)}</h1>"
        f'<p><span class="badge {badge_class}">{escape(overall.upper())}</span></p>'
    )


def _summary_table(report: PackageValidationReport) -> str:
    overall_dtd = report.overall_dtd_result
    rows = [
        ("Article ID", report.article_id),
        ("Overall Result", report.overall_result.value.upper()),
        ("Overall DTD Result", overall_dtd.value.upper() if overall_dtd else "Not checked"),
        ("Total Errors", str(report.total_errors)),
        ("Total Warnings", str(report.total_warnings)),
        ("Files Checked", str(len(report.files))),
    ]
    row_html = "".join(f"<tr><th>{escape(k)}</th><td>{escape(v)}</td></tr>" for k, v in rows)
    return f"<h2>Overview</h2><table>{row_html}</table>"


def _category_summary(report: PackageValidationReport) -> str:
    counts = report.category_counts
    if not counts:
        return (
            "<h2>Remaining DTD Findings by Category</h2>"
            '<p class="empty">No remaining DTD findings — every file is DTD-valid.</p>'
        )
    rows = "".join(
        f"<tr><th>{escape(_CATEGORY_LABELS.get(cat, cat))}</th><td>{count}</td></tr>"
        for cat, count in sorted(counts.items(), key=lambda kv: -kv[1])
    )
    return f"<h2>Remaining DTD Findings by Category</h2><table>{rows}</table>"


def _badge(label: str, result_value: str) -> str:
    badge_class = _BADGE_CLASS.get(result_value, "badge-warn")
    return (
        f'<span class="badge {badge_class}">{escape(label)}: {escape(result_value.upper())}</span>'
    )


def _file_section(file_report: FileValidationReport) -> str:
    dtd_status = (
        escape(file_report.dtd_name) if file_report.dtd_name else "No DTD applies to this file"
    )
    if file_report.dtd_name and not file_report.dtd_available:
        dtd_status += " (not vendored — DTD conformance not checked)"
    dtd_badge = (
        _badge("DTD", file_report.dtd_result.value)
        if file_report.dtd_result is not None
        else '<span class="badge badge-warn">DTD: NOT CHECKED</span>'
    )
    heading = (
        f"<h2>{escape(file_report.filename)}</h2>"
        f"<p>{_badge('Well-formed', file_report.well_formed_result.value)} {dtd_badge}</p>"
    )
    meta = (
        f'<p class="meta">DTD: {dtd_status} — Errors: {file_report.error_count}, '
        f"Warnings: {file_report.warning_count}</p>"
    )
    if not file_report.issues:
        return heading + meta + '<p class="empty">No issues found.</p>'
    rows = "".join(
        f"<tr><td>{escape(i.check or '—')}</td>"
        f"<td>{escape(i.severity.value.upper())}</td>"
        f"<td>{escape(i.message)}</td>"
        f"<td>{i.line if i.line is not None else '—'}</td>"
        f"<td>{escape(i.xpath) if i.xpath else '—'}</td>"
        f"<td>{escape(_CATEGORY_LABELS.get(i.category, '—')) if i.category else '—'}</td></tr>"
        for i in file_report.issues
    )
    table = (
        "<table><tr><th>Check</th><th>Severity</th><th>Message</th>"
        f"<th>Line</th><th>XPath</th><th>Category</th></tr>{rows}</table>"
    )
    return heading + meta + table
