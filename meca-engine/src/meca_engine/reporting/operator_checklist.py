"""Operator Checklist — Migration Audit / Traceability milestone.

The operational hand-off document: one page bucketing every article
into exactly the 4 groups an operator acts on. Buckets map directly to
existing, real :class:`~meca_engine.packaging.models.PackageStatus`
values — the same ones :mod:`meca_engine.service.router` already uses
to place a package under ``uploaded``/``manual_review``/``failed``
(routing itself is untouched):

- Ready to Upload: ``certified`` / ``certified_with_warnings`` /
  ``certified_with_recovery`` — the 3 statuses the router already
  places under ``uploaded``.
- Ready for Manual Review: ``partial_certification`` — the status the
  router already places under ``manual_review``.
- Needs Investigation: ``engine_failure`` — a defect in the engine
  itself, per that status's own docstring; actionable by the engine
  team.
- Failed: ``fatal_failure`` — the source data made safe generation
  impossible, per that status's own docstring; not an engine defect to
  chase.

The router treats the last two identically (both land under
``failed``); this document draws a real, already-documented
distinction between them for operator triage, without changing where
either package physically lands.
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.packaging.conversion_report import ConversionReport

_CSS = """
body { font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; }
body { margin: 2rem auto; max-width: 800px; color: #1a1a1a; line-height: 1.5; }
h1 { font-size: 1.5rem; border-bottom: 2px solid #ddd; padding-bottom: 0.5rem; }
h2 { font-size: 1.1rem; margin-top: 1.5rem; }
.badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; font-weight: 600; }
.badge-good { background: #e6f4ea; color: #1e7e34; }
.badge-warn { background: #fff8e1; color: #8a6d00; }
.badge-bad { background: #fdecea; color: #b3261e; }
ul { margin: 0.25rem 0; }
.empty { color: #888; font-style: italic; }
"""

_BUCKETS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "Ready to Upload",
        "badge-good",
        ("certified", "certified_with_warnings", "certified_with_recovery"),
    ),
    ("Ready for Manual Review", "badge-warn", ("partial_certification",)),
    ("Needs Investigation", "badge-bad", ("engine_failure",)),
    ("Failed", "badge-bad", ("fatal_failure",)),
)


def render_operator_checklist(reports: list[ConversionReport]) -> str:
    """Render the whole batch's Operator Checklist as a self-contained HTML string."""
    sections = []
    for label, badge_class, statuses in _BUCKETS:
        matching = [r for r in reports if r.status.value in statuses]
        items = "".join(f"<li>{escape(r.article_id)}</li>" for r in matching)
        sections.append(
            f'<h2>{escape(label)} <span class="badge {badge_class}">{len(matching)}</span></h2>'
            + (f"<ul>{items}</ul>" if matching else '<p class="empty">None.</p>')
        )
    body = "<h1>Operator Checklist</h1>" + "".join(sections)
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>Operator Checklist</title><style>{_CSS}</style></head>"
        f"<body>\n{body}\n</body></html>\n"
    )


def write_operator_checklist(reports: list[ConversionReport], output_path: Path) -> None:
    """Render and write the whole batch's Operator Checklist to disk."""
    output_path.write_text(render_operator_checklist(reports), encoding="utf-8")
