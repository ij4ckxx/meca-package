"""Migration trend analysis — Milestone 14.

Compares batch runs over time. A "trend" requires at least two
snapshots; with only one (the common case until this milestone has run
more than once), this module reports a single baseline point rather than
inventing a direction — see :func:`analyze_trends`'s ``"status"`` field.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from meca_engine.reporting.intelligence.confidence_statistics import compute_confidence_statistics

if TYPE_CHECKING:
    from meca_engine.reporting.intelligence.corpus_analyzer import ArticleRecord


@dataclass(frozen=True)
class BatchSnapshot:
    """One batch run's records, labeled (e.g. by date or run ID)."""

    label: str
    records: tuple[ArticleRecord, ...]


@dataclass(frozen=True)
class TrendPoint:
    """One snapshot's headline metrics, for comparison across snapshots."""

    label: str
    total_articles: int
    status_counts: dict[str, int]
    average_confidence_score: float
    recovery_rate: float  # fraction of articles with >=1 recovery rule applied

    def to_dict(self) -> dict[str, Any]:
        """Render as a plain, ``json.dumps``-ready dict."""
        return {
            "label": self.label,
            "total_articles": self.total_articles,
            "status_counts": self.status_counts,
            "average_confidence_score": round(self.average_confidence_score, 1),
            "recovery_rate": round(self.recovery_rate, 3),
        }


def _trend_point(snapshot: BatchSnapshot) -> TrendPoint:
    records = snapshot.records
    status_counts: dict[str, int] = {}
    for record in records:
        status_counts[record.status] = status_counts.get(record.status, 0) + 1
    confidence = compute_confidence_statistics(records)
    recovery_rate = (
        sum(1 for r in records if r.recovery_rules_triggered) / len(records) if records else 0.0
    )
    return TrendPoint(
        label=snapshot.label,
        total_articles=len(records),
        status_counts=status_counts,
        average_confidence_score=confidence.average_score,
        recovery_rate=recovery_rate,
    )


def analyze_trends(snapshots: list[BatchSnapshot]) -> dict[str, Any]:
    """Compare a sequence of batch snapshots; a single snapshot yields a baseline only."""
    if not snapshots:
        return {"status": "no_data", "points": [], "deltas": []}

    points = [_trend_point(s) for s in snapshots]
    if len(points) == 1:
        return {
            "status": "insufficient_history",
            "note": "Only one batch run is available. Trend direction requires at least two.",
            "points": [p.to_dict() for p in points],
            "deltas": [],
        }

    deltas = []
    for previous, current in zip(points, points[1:]):  # noqa: B905
        deltas.append(
            {
                "from": previous.label,
                "to": current.label,
                "confidence_score_delta": round(
                    current.average_confidence_score - previous.average_confidence_score, 1
                ),
                "recovery_rate_delta": round(current.recovery_rate - previous.recovery_rate, 3),
                "total_articles_delta": current.total_articles - previous.total_articles,
            }
        )
    return {
        "status": "computed",
        "points": [p.to_dict() for p in points],
        "deltas": deltas,
    }


def build_trends_json(snapshots: list[BatchSnapshot]) -> dict[str, Any]:
    """Assemble ``Migration_Trends.json`` for a sequence of batch snapshots."""
    return analyze_trends(snapshots)
