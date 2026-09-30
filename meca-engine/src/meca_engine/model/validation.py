"""Structural integrity validation for the Internal Canonical Article Model.

Per this milestone's explicit scope: **only** structural integrity is
checked here — required internal references, duplicate-object detection,
and graph consistency. No publishing business rule is ever applied (that
remains the Business-Rule-Book-driven Validation Engine's job, a later
milestone, `validation.engine.ValidationEngine`, 11_LLD_02... §4.8).

Immutable-state validation itself (the "no mutation permitted" guarantee)
is provided structurally by every ICAM type being a frozen dataclass —
attempting to set an attribute on a frozen instance raises
``dataclasses.FrozenInstanceError`` unconditionally, verified by this
milestone's tests. There is nothing for a runtime checker to additionally
verify beyond that language-level guarantee.

Every check here returns a `StructuralIssue`, never raises — consistent
with the diagnostics-not-exceptions pattern established in Milestone 4
(`extraction.diagnostics`): a structurally inconsistent ICAM is a defect
to report, not (at this layer) a reason to halt article processing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meca_engine.logging_.structured_logger import StructuredLogger
    from meca_engine.model.article import ArticleModel


@unique
class StructuralIssueSeverity(str, Enum):
    """Severity of one structural-integrity issue."""

    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class StructuralIssue:
    """One structural-integrity observation about an `ArticleModel` instance.

    Attributes:
        severity: How serious this observation is.
        code: A short, stable machine-readable identifier (e.g.
            ``"DUPLICATE_AFFILIATION_KEY"``).
        message: A human-readable description.
    """

    severity: StructuralIssueSeverity
    code: str
    message: str


def validate_structural_integrity(
    article: ArticleModel, *, logger: StructuredLogger | None = None
) -> tuple[StructuralIssue, ...]:
    """Check an `ArticleModel` instance for structural (not business-rule) integrity.

    Args:
        article: The frozen model to check.
        logger: Optional structured logger; logs a start event and a
            completion event carrying the issue count when given.

    Returns:
        Every structural issue found, in a fixed check order (affiliation
        keys, contributor references, round consistency). Empty when the
        model is structurally sound.
    """
    if logger is not None:
        logger.info(
            "Validating ArticleModel structural integrity",
            stage="model.validation",
            context={"article_id": article.identity.article_id},
        )

    issues: list[StructuralIssue] = []
    issues.extend(_check_duplicate_affiliation_keys(article))
    issues.extend(_check_dangling_affiliation_references(article))
    issues.extend(_check_round_index_consistency(article))

    if logger is not None:
        logger.info(
            "ArticleModel structural integrity check complete",
            stage="model.validation",
            context={
                "article_id": article.identity.article_id,
                "issue_count": len(issues),
            },
        )
    return tuple(issues)


def _check_duplicate_affiliation_keys(article: ArticleModel) -> tuple[StructuralIssue, ...]:
    seen: set[int] = set()
    issues: list[StructuralIssue] = []
    for affiliation in article.article_meta.affiliations:
        if affiliation.model_key in seen:
            issues.append(
                StructuralIssue(
                    severity=StructuralIssueSeverity.ERROR,
                    code="DUPLICATE_AFFILIATION_KEY",
                    message=f"Affiliation model_key {affiliation.model_key} is not unique",
                )
            )
        else:
            seen.add(affiliation.model_key)
    return tuple(issues)


def _check_dangling_affiliation_references(article: ArticleModel) -> tuple[StructuralIssue, ...]:
    valid_keys = {a.model_key for a in article.article_meta.affiliations}
    issues: list[StructuralIssue] = []
    for contributor in article.article_meta.contributors:
        for key in contributor.affiliation_keys:
            if key not in valid_keys:
                issues.append(
                    StructuralIssue(
                        severity=StructuralIssueSeverity.ERROR,
                        code="DANGLING_AFFILIATION_KEY",
                        message=(
                            f"Contributor {contributor.surname!r} references affiliation_key "
                            f"{key}, which does not exist in this article's AffiliationList"
                        ),
                    )
                )
    return tuple(issues)


def _check_round_index_consistency(article: ArticleModel) -> tuple[StructuralIssue, ...]:
    issues: list[StructuralIssue] = []
    if article.rounds:
        latest_count = sum(1 for r in article.rounds if r.is_latest)
        if latest_count != 1:
            issues.append(
                StructuralIssue(
                    severity=StructuralIssueSeverity.ERROR,
                    code="ROUND_LATEST_COUNT_INVALID",
                    message=(
                        f"Expected exactly one RoundInfo.is_latest=True, found {latest_count}"
                    ),
                )
            )
    seen_sequences: set[int] = set()
    for round_info in article.rounds:
        if round_info.sequence_number in seen_sequences:
            issues.append(
                StructuralIssue(
                    severity=StructuralIssueSeverity.ERROR,
                    code="DUPLICATE_ROUND_SEQUENCE",
                    message=(f"Round sequence_number {round_info.sequence_number} is not unique"),
                )
            )
        else:
            seen_sequences.add(round_info.sequence_number)
    return tuple(issues)
