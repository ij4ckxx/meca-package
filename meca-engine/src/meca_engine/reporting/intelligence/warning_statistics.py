"""Warning frequency and outcome-correlation statistics — Milestone 14.

Groups every advisory finding — both `EngineWarning` entries (identified
by their stable `.code`) and `GeneratorDiagnostic` entries (identified by
a normalized version of their message, since that type carries no
stable code of its own, Milestone 6A design, unchanged here) — and
tracks whether every article carrying a given warning still certified
successfully. That correlation is the evidence the recommendation
engine's dashboard-suppression rule needs.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.reporting.intelligence.corpus_analyzer import ArticleRecord

_QUOTED_SPAN = re.compile(r"'[^']*'")


@dataclass(frozen=True)
class WarningStats:
    """One distinct warning pattern's observed frequency and outcomes."""

    code: str
    source: str  # "engine_warning" | "generator_diagnostic"
    sample_message: str
    occurrences: int
    articles_affected: int
    always_successful: bool

    def to_dict(self) -> dict[str, Any]:
        """Render as a plain, ``json.dumps``-ready dict."""
        return {
            "code": self.code,
            "source": self.source,
            "sample_message": self.sample_message,
            "occurrences": self.occurrences,
            "articles_affected": self.articles_affected,
            "always_successful": self.always_successful,
        }


def _normalize_message(message: str) -> str:
    return _QUOTED_SPAN.sub("'<X>'", message)


def compute_warning_statistics(records: tuple[ArticleRecord, ...]) -> list[WarningStats]:
    """Compute one :class:`WarningStats` per distinct warning pattern observed."""
    occurrences: Counter[str] = Counter()
    articles_affected: Counter[str] = Counter()
    always_successful: dict[str, bool] = {}
    sample_message: dict[str, str] = {}
    source: dict[str, str] = {}

    for record in records:
        seen_this_article: set[str] = set()
        for warning in (*record.source.warnings, *record.source.recoveries):
            _record_occurrence(
                warning.code,
                "engine_warning",
                warning.message,
                record.succeeded,
                seen_this_article,
                occurrences,
                articles_affected,
                always_successful,
                sample_message,
                source,
            )
        for diagnostic in record.source.generator_findings:
            key = _normalize_message(diagnostic.message)
            _record_occurrence(
                key,
                "generator_diagnostic",
                diagnostic.message,
                record.succeeded,
                seen_this_article,
                occurrences,
                articles_affected,
                always_successful,
                sample_message,
                source,
            )

    return [
        WarningStats(
            code=code,
            source=source[code],
            sample_message=sample_message[code],
            occurrences=occurrences[code],
            articles_affected=articles_affected[code],
            always_successful=always_successful[code],
        )
        for code in occurrences
    ]


def _record_occurrence(
    key: str,
    source_kind: str,
    message: str,
    succeeded: bool,
    seen_this_article: set[str],
    occurrences: Counter[str],
    articles_affected: Counter[str],
    always_successful: dict[str, bool],
    sample_message: dict[str, str],
    source: dict[str, str],
) -> None:
    occurrences[key] += 1
    if key not in seen_this_article:
        seen_this_article.add(key)
        articles_affected[key] += 1
    always_successful[key] = always_successful.get(key, True) and succeeded
    sample_message.setdefault(key, message)
    source.setdefault(key, source_kind)


def render_warning_frequency(records: tuple[ArticleRecord, ...]) -> str:
    """Render ``Warning_Frequency.md`` for a batch of articles."""
    stats = sorted(compute_warning_statistics(records), key=lambda s: -s.occurrences)
    lines = [
        "# Warning Frequency",
        "",
        "| Warning | Source | Occurrences | Articles | Always Certified |",
        "|---|---|---|---|---|",
    ]
    for s in stats:
        label = s.code if s.source == "engine_warning" else s.sample_message
        lines.append(
            f"| {label} | {s.source} | {s.occurrences} | {s.articles_affected} | "
            f"{'yes' if s.always_successful else 'no'} |"
        )
    if not stats:
        lines.append("| — | — | 0 | 0 | — |")
    return "\n".join(lines)


def write_warning_frequency(records: tuple[ArticleRecord, ...], output_path: Path) -> None:
    """Render and write ``Warning_Frequency.md`` to disk."""
    output_path.write_text(render_warning_frequency(records), encoding="utf-8")
