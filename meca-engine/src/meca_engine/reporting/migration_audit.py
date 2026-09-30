"""Migration Audit Report — Migration Audit / Traceability milestone.

Answers, for one already-built package, exactly the questions this
milestone requires: what changed, why, which Business/Recovery Rules
fired, which warnings/source/DTD problems remain, what confidence to
place in the package, who/what produced it, and whether it can be
reproduced. Reads only fields already on
:class:`~meca_engine.packaging.conversion_report.ConversionReport`
(including its new, purely additive ``reproducibility`` field from this
same milestone) — no new business logic, no change to any generator,
Business Rule, or Recovery Rule. Where a fact the milestone asks for
(an XPath, an input/output XML location) is not tracked anywhere in the
engine, the corresponding field is left blank rather than invented —
see ``_build_rule_traceability``.

:func:`build_migration_audit_data` is the single source of truth both
the HTML report and ``migration-audit.json`` are built from, so the two
can never drift apart.
"""

from __future__ import annotations

import json
from html import escape
from typing import TYPE_CHECKING, Any

from meca_engine.model.recovery_rules import ALL_RECOVERY_RULES

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.model.warnings import EngineWarning
    from meca_engine.packaging.conversion_report import BusinessRuleFinding, ConversionReport

_RECOVERY_RULE_BY_ID = {rule.rule_id: rule for rule in ALL_RECOVERY_RULES}

# Mirrors `certification_report.py`'s own status labels — duplicated
# rather than imported, matching this codebase's existing convention of
# each report renderer keeping its own small presentation constants
# (e.g. `validation_report.py` already does the same for its badges).
_STATUS_LABELS = {
    "certified": "Certified",
    "certified_with_warnings": "Certified — with warnings",
    "certified_with_recovery": "Certified — with recovery",
    "partial_certification": "Partially certified",
    "engine_failure": "Not generated — engine failure",
    "fatal_failure": "Not generated — fatal source-data failure",
}

_BADGE_CLASS = {
    "certified": "badge-good",
    "certified_with_warnings": "badge-good",
    "certified_with_recovery": "badge-good",
    "partial_certification": "badge-warn",
    "engine_failure": "badge-bad",
    "fatal_failure": "badge-bad",
    "pass": "badge-good",
    "warning": "badge-warn",
    "error": "badge-bad",
}

_CSS = """
body { font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; }
body { margin: 2rem auto; max-width: 900px; color: #1a1a1a; line-height: 1.5; }
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
.note { color: #888; font-size: 0.85rem; font-style: italic; margin: 0.25rem 0 1rem; }
ul { margin: 0.25rem 0; }
"""


def _warning_row(warning: EngineWarning) -> dict[str, Any]:
    return {
        "code": warning.code,
        "rule_id": warning.rule_id,
        "recovery_rule_id": warning.recovery_rule_id,
        "severity": warning.severity.value,
        "confidence": warning.confidence.value,
        "message": warning.message,
        "affected_file": warning.affected_file,
        "suggested_action": warning.suggested_action,
        "is_recovery": warning.is_recovery,
    }


def _build_business_rule_states(
    findings: tuple[BusinessRuleFinding, ...],
    recoveries: tuple[EngineWarning, ...],
    business_rules_passed: tuple[str, ...],
) -> dict[str, list[str]]:
    """Partition every Business Rule mentioned by a finding into 6 states.

    Honest about what the engine actually tracks: ``passed`` is real but
    limited to the small tracked subset already on ``ConversionReport``
    (``business_rules_passed`` — see that field's own docstring);
    ``skipped`` has no engine concept at all today and is always empty,
    not fabricated as a real observation. Every other bucket is derived
    directly from ``BusinessRuleFinding.severity`` and ``EngineWarning.is_recovery``
    — real, existing fields, no new signal invented.
    """
    by_severity: dict[str, set[str]] = {"info": set(), "warning": set(), "error": set()}
    for finding in findings:
        by_severity.setdefault(finding.severity, set()).add(finding.rule_id)

    recovered_ids = {w.rule_id for w in recoveries if w.rule_id}
    failed_ids = by_severity.get("error", set())
    warning_ids = by_severity.get("warning", set()) - recovered_ids - failed_ids
    applied_ids = by_severity.get("info", set()) - recovered_ids - warning_ids - failed_ids
    recovery_ids = recovered_ids - failed_ids

    return {
        "passed": sorted(business_rules_passed),
        "applied": sorted(applied_ids),
        "warning": sorted(warning_ids),
        "recovery": sorted(recovery_ids),
        "skipped": [],
        "failed": sorted(failed_ids),
    }


def _build_recovery_rule_rows(recoveries: tuple[EngineWarning, ...]) -> list[dict[str, Any]]:
    rows = []
    for warning in recoveries:
        rule = _RECOVERY_RULE_BY_ID.get(warning.recovery_rule_id or "")
        rows.append(
            {
                "rule_id": warning.recovery_rule_id,
                "name": rule.name if rule else None,
                "applied_to": warning.affected_file,
                "confidence": warning.confidence.value,
                "reason": rule.description if rule else warning.message,
            }
        )
    return rows


def _build_rule_traceability(
    findings: tuple[BusinessRuleFinding, ...],
    warnings: tuple[EngineWarning, ...],
    recoveries: tuple[EngineWarning, ...],
) -> list[dict[str, Any]]:
    """Input XML location -> Rule -> Output XML location, per finding.

    Neither location is tracked anywhere in the engine today (confirmed:
    the only XPath the engine ever records is on a DTD validation
    finding, an unrelated signal) — both are always left blank here
    rather than invented, per this milestone's explicit instruction.
    ``affected_file`` is real, reused from a matching
    :class:`EngineWarning` (by ``rule_id``) when one exists.
    """
    affected_file_by_rule: dict[str, str] = {}
    for warning in (*warnings, *recoveries):
        if (
            warning.rule_id
            and warning.affected_file
            and warning.rule_id not in affected_file_by_rule
        ):
            affected_file_by_rule[warning.rule_id] = warning.affected_file

    return [
        {
            "rule_id": finding.rule_id,
            "message": finding.message,
            "severity": finding.severity,
            "source": finding.source,
            "affected_file": affected_file_by_rule.get(finding.rule_id, ""),
            "input_xml_location": "",
            "output_xml_location": "",
        }
        for finding in findings
    ]


def build_migration_audit_data(report: ConversionReport) -> dict[str, Any]:
    """Build the single data structure both the HTML report and JSON audit reuse."""
    validation = report.validation_report
    dtd_problems = []
    if validation is not None:
        for file_report in validation.files:
            for issue in file_report.issues:
                if issue.check == "dtd":
                    dtd_problems.append(
                        {
                            "filename": file_report.filename,
                            "severity": issue.severity.value,
                            "message": issue.message,
                            "line": issue.line,
                            "xpath": issue.xpath,
                            "category": issue.category,
                        }
                    )

    source_problems: list[dict[str, Any]] = [
        {"type": "missing_metadata", "detail": item} for item in report.missing_metadata
    ]
    source_problems.extend(
        {"type": "missing_file", "detail": item} for item in report.missing_files
    )
    if validation is not None:
        for file_report in validation.files:
            for issue in file_report.issues:
                if issue.category == "source_data_issue":
                    source_problems.append(
                        {
                            "type": "source_data_issue",
                            "detail": f"{file_report.filename}: {issue.message}",
                        }
                    )

    return {
        "article_id": report.article_id,
        "package_status": report.status.value,
        "certification_status_label": _STATUS_LABELS.get(report.status.value, report.status.value),
        "confidence_score": report.confidence_score,
        "overall_confidence": report.overall_confidence.value,
        "journal": report.journal,
        "reproducibility": report.reproducibility.to_dict() if report.reproducibility else None,
        "rule_statistics": {
            "business_rules": _build_business_rule_states(
                report.business_rule_findings, report.recoveries, report.business_rules_passed
            ),
            "recovery_rules": _build_recovery_rule_rows(report.recoveries),
        },
        "warnings": [_warning_row(w) for w in report.warnings],
        "fatal_issues": (
            [report.unrecoverable_error.to_dict()] if report.unrecoverable_error else []
        ),
        "remaining_source_problems": source_problems,
        "remaining_dtd_problems": dtd_problems,
        "files": {
            "generated": list(report.generated_files),
            "missing": list(report.missing_files),
        },
        "validation_summary": validation.to_dict() if validation is not None else None,
        "rule_traceability": _build_rule_traceability(
            report.business_rule_findings, report.warnings, report.recoveries
        ),
    }


def render_migration_audit_report(report: ConversionReport) -> str:
    """Render one package's Migration Audit Report as a self-contained HTML string."""
    data = build_migration_audit_data(report)
    sections = [
        _header(report, data),
        _summary_table(report, data),
        _reproducibility_section(data),
        _business_rule_section(data),
        _recovery_rule_section(data),
        _warnings_section(data),
        _fatal_section(data),
        _source_problems_section(data),
        _dtd_problems_section(data),
        _files_section(data),
        _validation_summary_section(data),
        _rule_traceability_section(data),
    ]
    body = "\n".join(sections)
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>Migration Audit Report — {escape(report.article_id)}</title>"
        f"<style>{_CSS}</style></head><body>\n{body}\n</body></html>\n"
    )


def write_migration_audit_report(report: ConversionReport, output_path: Path) -> None:
    """Render and write one package's Migration Audit Report to disk."""
    output_path.write_text(render_migration_audit_report(report), encoding="utf-8")


def write_migration_audit_json(report: ConversionReport, output_path: Path) -> None:
    """Write one package's machine-readable ``migration-audit.json``."""
    payload = json.dumps(build_migration_audit_data(report), indent=2)
    output_path.write_text(payload, encoding="utf-8")


def _header(report: ConversionReport, data: dict[str, Any]) -> str:
    badge_class = _BADGE_CLASS.get(data["package_status"], "badge-warn")
    status_label = escape(data["certification_status_label"])
    return (
        f"<h1>Migration Audit Report — {escape(report.article_id)}</h1>"
        f'<p><span class="badge {badge_class}">{status_label}</span></p>'
    )


def _summary_table(report: ConversionReport, data: dict[str, Any]) -> str:
    repro = data["reproducibility"] or {}
    rows = [
        ("Article ID", report.article_id),
        ("Journal", data["journal"] or "—"),
        ("Package Status", data["certification_status_label"]),
        ("Confidence", f"{data['confidence_score']}/100 ({data['overall_confidence']})"),
        ("Generated Time", repro.get("generation_timestamp", "—")),
        ("Engine Version", repro.get("engine_version", "—")),
    ]
    row_html = "".join(f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>" for k, v in rows)
    return f"<h2>Overview</h2><table>{row_html}</table>"


def _reproducibility_section(data: dict[str, Any]) -> str:
    repro = data["reproducibility"]
    if repro is None:
        return '<h2>Reproducibility</h2><p class="empty">Not recorded for this package.</p>'
    rows = [
        ("Engine Version", repro["engine_version"]),
        ("Business Rule Book Version", repro["business_rule_book_version"]),
        ("Recovery Rule Version", repro["recovery_rule_version"]),
        ("DTD Version", repro["dtd_version"]),
        ("Configuration Checksum", repro["config_checksum"]),
        ("Generation Timestamp", repro["generation_timestamp"]),
        ("Python Version", repro["python_version"]),
        ("Operating System", repro["operating_system"]),
    ]
    row_html = "".join(f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>" for k, v in rows)
    return f"<h2>Reproducibility</h2><table>{row_html}</table>"


def _business_rule_section(data: dict[str, Any]) -> str:
    states = data["rule_statistics"]["business_rules"]
    labels = [
        ("passed", "Passed"),
        ("applied", "Applied"),
        ("warning", "Warning"),
        ("recovery", "Recovery"),
        ("skipped", "Skipped"),
        ("failed", "Failed"),
    ]
    rows = "".join(
        f"<tr><th>{label}</th><td>{len(states[key])}</td>"
        f"<td>{escape(', '.join(states[key])) if states[key] else '—'}</td></tr>"
        for key, label in labels
    )
    note = (
        '<p class="note">"Passed" reflects only the small subset of Business Rules this '
        'engine tracks explicit pass/fail signal for. "Skipped" has no engine concept '
        "today and is always empty, not a real zero observation.</p>"
    )
    return (
        f"<h2>Business Rule Statistics</h2>"
        f"<table><tr><th>State</th><th>Count</th><th>Rule IDs</th></tr>{rows}</table>{note}"
    )


def _recovery_rule_section(data: dict[str, Any]) -> str:
    rows = data["rule_statistics"]["recovery_rules"]
    if not rows:
        return '<h2>Recovery Rules Applied</h2><p class="empty">None.</p>'
    body = "".join(
        f"<tr><td>{escape(r['rule_id'] or '—')}</td>"
        f"<td>{escape(r['name'] or '—')}</td>"
        f"<td>{escape(r['applied_to'] or '—')}</td>"
        f"<td>{escape(r['confidence'])}</td>"
        f"<td>{escape(r['reason'])}</td></tr>"
        for r in rows
    )
    return (
        "<h2>Recovery Rules Applied</h2><table>"
        f"<tr><th>Rule</th><th>Name</th><th>Applied To</th><th>Confidence</th><th>Reason</th></tr>"
        f"{body}</table>"
    )


def _warnings_section(data: dict[str, Any]) -> str:
    warnings = data["warnings"]
    if not warnings:
        return '<h2>Warnings Remaining</h2><p class="empty">None.</p>'
    items = "".join(
        f"<li>[{escape(w['severity'])}] {escape(w['message'])}"
        + (f" <em>(file: {escape(w['affected_file'])})</em>" if w["affected_file"] else "")
        + "</li>"
        for w in warnings
    )
    return f"<h2>Warnings Remaining ({len(warnings)})</h2><ul>{items}</ul>"


def _fatal_section(data: dict[str, Any]) -> str:
    fatal = data["fatal_issues"]
    if not fatal:
        return '<h2>Fatal Issues</h2><p class="empty">None.</p>'
    items = "".join(f"<li>{escape(e['stage'])}: {escape(e['message'])}</li>" for e in fatal)
    return f"<h2>Fatal Issues</h2><ul>{items}</ul>"


def _source_problems_section(data: dict[str, Any]) -> str:
    problems = data["remaining_source_problems"]
    if not problems:
        return '<h2>Remaining Source Problems</h2><p class="empty">None.</p>'
    items = "".join(f"<li>[{escape(p['type'])}] {escape(p['detail'])}</li>" for p in problems)
    return f"<h2>Remaining Source Problems ({len(problems)})</h2><ul>{items}</ul>"


def _dtd_problems_section(data: dict[str, Any]) -> str:
    problems = data["remaining_dtd_problems"]
    if not problems:
        return '<h2>Remaining DTD Problems</h2><p class="empty">None — fully DTD-valid.</p>'
    rows = "".join(
        f"<tr><td>{escape(p['filename'])}</td><td>{escape(p['severity'])}</td>"
        f"<td>{escape(p['message'])}</td><td>{escape(p['category'] or '—')}</td></tr>"
        for p in problems
    )
    return (
        f"<h2>Remaining DTD Problems ({len(problems)})</h2>"
        f"<table><tr><th>File</th><th>Severity</th><th>Message</th><th>Category</th></tr>{rows}</table>"
    )


def _files_section(data: dict[str, Any]) -> str:
    generated = data["files"]["generated"]
    missing = data["files"]["missing"]
    parts = [f"<h2>Files Generated ({len(generated)})</h2>"]
    parts.append(
        "<ul>" + "".join(f"<li>{escape(f)}</li>" for f in generated) + "</ul>"
        if generated
        else '<p class="empty">None.</p>'
    )
    parts.append(f"<h2>Files Missing ({len(missing)})</h2>")
    parts.append(
        "<ul>" + "".join(f"<li>{escape(f)}</li>" for f in missing) + "</ul>"
        if missing
        else '<p class="empty">None.</p>'
    )
    return "".join(parts)


def _validation_summary_section(data: dict[str, Any]) -> str:
    validation = data["validation_summary"]
    if validation is None:
        return '<h2>Validation Summary</h2><p class="empty">Not available for this package.</p>'
    rows = [
        ("Overall Result", validation["overall_result"]),
        ("Overall DTD Result", validation["overall_dtd_result"] or "not checked"),
        ("Total Errors", str(validation["total_errors"])),
        ("Total Warnings", str(validation["total_warnings"])),
    ]
    row_html = "".join(f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>" for k, v in rows)
    return f"<h2>Validation Summary</h2><table>{row_html}</table>"


def _rule_traceability_section(data: dict[str, Any]) -> str:
    rows = data["rule_traceability"]
    if not rows:
        return (
            "<h2>Rule Traceability</h2>"
            '<p class="empty">No Business Rule findings for this package.</p>'
        )
    body = "".join(
        f"<tr><td>{escape(r['input_xml_location']) or '—'}</td>"
        f"<td>{escape(r['rule_id'])}</td>"
        f"<td>{escape(r['output_xml_location']) or '—'}</td>"
        f"<td>{escape(r['message'])}</td>"
        f"<td>{escape(r['affected_file']) or '—'}</td></tr>"
        for r in rows
    )
    note = (
        '<p class="note">Input/output XML location columns are left blank when the engine '
        "does not track element-level location for a finding — never fabricated.</p>"
    )
    return (
        "<h2>Rule Traceability</h2>"
        "<table><tr><th>Input XML Location</th><th>Rule</th><th>Output XML Location</th>"
        f"<th>Message</th><th>Affected File</th></tr>{body}</table>{note}"
    )
