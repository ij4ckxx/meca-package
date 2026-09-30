"""Archive_Audit.csv and Manual_Review.csv — Milestone 13.

Plain, Excel-importable CSV exports built from a batch of
:class:`~meca_engine.packaging.conversion_report.ConversionReport`.
"""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.packaging.conversion_report import ConversionReport

_AUDIT_FIELDNAMES = (
    "Article ID",
    "Journal",
    "Status",
    "Confidence",
    "Recovery Count",
    "Warning Count",
    "Missing Files",
    "Missing Metadata",
    "Generated Package",
)

_REVIEW_FIELDNAMES = (
    "Article",
    "Reason",
    "Severity",
    "Suggested Action",
    "Estimated Review Priority",
)

# Lower number = review sooner.
_SEVERITY_PRIORITY = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}


def write_archive_audit_csv(reports: list[ConversionReport], output_path: Path) -> None:
    """Write one row per article to ``Archive_Audit.csv``."""
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_AUDIT_FIELDNAMES)
        writer.writeheader()
        for report in reports:
            writer.writerow(_audit_row(report))


def _audit_row(report: ConversionReport) -> dict[str, str]:
    generated = report.unrecoverable_error is None
    return {
        "Article ID": report.article_id,
        "Journal": report.journal,
        "Status": report.status.value,
        "Confidence": report.overall_confidence.value,
        "Recovery Count": str(len(report.recoveries)),
        "Warning Count": str(len(report.warnings) + len(report.generator_findings)),
        "Missing Files": "; ".join(report.missing_files),
        "Missing Metadata": "; ".join(report.missing_metadata),
        "Generated Package": "yes" if generated else "no",
    }


def build_manual_review_rows(reports: list[ConversionReport]) -> list[dict[str, str]]:
    """Select and describe the articles that require human attention.

    An article is included if any of:

    - Its status is ``PARTIAL_CERTIFICATION``, ``ENGINE_FAILURE``, or
      ``FATAL_FAILURE`` (real content missing, or no package at all).
    - Its overall confidence is ``LOW``.
    - Any individual recovery has ``LOW`` confidence (a heuristic match
      worth a spot-check even if the overall package still scores well).
    """
    rows: list[dict[str, str]] = []
    for report in reports:
        reasons = _review_reasons(report)
        if not reasons:
            continue
        severity = _severity_for(report)
        rows.append(
            {
                "Article": report.article_id,
                "Reason": "; ".join(reasons),
                "Severity": severity,
                "Suggested Action": _suggested_action(report),
                "Estimated Review Priority": str(_SEVERITY_PRIORITY[severity]),
            }
        )
    rows.sort(key=lambda row: int(row["Estimated Review Priority"]))
    return rows


def write_manual_review_csv(reports: list[ConversionReport], output_path: Path) -> None:
    """Write ``Manual_Review.csv`` — only articles requiring human attention."""
    rows = build_manual_review_rows(reports)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_REVIEW_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _review_reasons(report: ConversionReport) -> list[str]:
    reasons: list[str] = []
    status = report.status.value
    if status == "partial_certification":
        reasons.append(f"Missing files: {', '.join(report.missing_files)}")
    if status in ("engine_failure", "fatal_failure") and report.unrecoverable_error:
        reasons.append(f"Package not generated: {report.unrecoverable_error.message}")
    if report.overall_confidence.value == "low" and status not in (
        "partial_certification",
        "engine_failure",
        "fatal_failure",
    ):
        reasons.append("Overall confidence is low")
    low_confidence_recoveries = [r for r in report.recoveries if r.confidence.value == "low"]
    if low_confidence_recoveries and status not in ("engine_failure", "fatal_failure"):
        reasons.append(f"{len(low_confidence_recoveries)} low-confidence file match(es)")
    return reasons


def _severity_for(report: ConversionReport) -> str:
    status = report.status.value
    if status in ("engine_failure", "fatal_failure", "partial_certification"):
        return "HIGH"
    if report.overall_confidence.value == "low":
        return "MEDIUM"
    return "LOW"


def _suggested_action(report: ConversionReport) -> str:
    status = report.status.value
    if status == "fatal_failure":
        return "Investigate the source archive; safe generation was not possible."
    if status == "engine_failure":
        return "Investigate the engine defect; this is not a source-data issue."
    if status == "partial_certification":
        return "Confirm the missing file(s) are not required for archival completeness."
    if report.overall_confidence.value == "low":
        return "Review the recoveries applied before archival sign-off."
    return "Spot-check the low-confidence file match(es)."
