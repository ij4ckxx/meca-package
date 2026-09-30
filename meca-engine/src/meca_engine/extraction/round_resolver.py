"""Round resolution — Milestone 5B (11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.4).

Builds the ICAM's ``RoundIndex`` directly from a Milestone 3
:class:`~meca_engine.extraction.parsed_model.ParsedDocument`'s
``<article-version>`` element(s) — the only documented source for
round-ordering (Business Rule Book BR-010: "the ``vocab-identifier``
snapshot number is the round-ordering key"). Deliberately reads the raw
parsed tree rather than any Milestone 4 extractor output: Milestone 4's
seven extractors never captured ``article-version``/``vocab-identifier``
(out of scope for their seven named areas), so this module — like
Milestone 4's extractors — is a thin, additional, independent reader of
the same generic :mod:`~meca_engine.extraction.navigation` helpers.

Per ADR-013, this must never silently guess a sequence number or a round
label — an ``<article-version>`` whose ``vocab-identifier`` doesn't match
the documented ``"snapshots/<N>_..."`` format, or that lacks an
``article-version-type`` attribute, raises :class:`RoundResolutionError`
rather than defaulting.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from meca_engine.exceptions import RoundResolutionError
from meca_engine.extraction.navigation import find_all, get_attribute
from meca_engine.model.article import RoundInfo
from meca_engine.model.recovery_rules import (
    RR_005_DUPLICATE_ROUND_DEDUPED,
    RR_006_MALFORMED_ROUND_SKIPPED,
)
from meca_engine.model.warnings import (
    ConfidenceLevel,
    EngineWarning,
    FindingOrigin,
    WarningCategory,
    WarningSeverity,
)

if TYPE_CHECKING:
    from meca_engine.extraction.parsed_model import ParsedDocument

_STAGE = "extraction.round_resolver"
_VOCAB_IDENTIFIER_SEQUENCE_PATTERN = re.compile(r"^snapshots/(\d+)_")
_MALFORMED_VERSION_WARNING_CODE = "BR010_MALFORMED_ARTICLE_VERSION_SKIPPED"
_DUPLICATE_SEQUENCE_WARNING_CODE = "BR010_DUPLICATE_SEQUENCE_DEDUPED"


def resolve_rounds(
    document: ParsedDocument, *, article_id: str | None = None
) -> tuple[tuple[RoundInfo, ...], tuple[EngineWarning, ...]]:
    """Resolve the round index from a parsed document's ``<article-version>`` element(s).

    Args:
        document: The parsed document to read from.
        article_id: The article this resolution is for, attached to any
            raised :class:`RoundResolutionError` for context.

    Returns:
        A ``(rounds, warnings)`` pair. ``rounds`` has one
        :class:`~meca_engine.model.article.RoundInfo` per distinct,
        resolvable ``<article-version>`` element, ordered by ascending
        ``sequence_number``, with exactly the highest-numbered entry
        marked ``is_latest=True``. Empty if the document has no
        ``<article-version>`` element at all (not itself an error — a
        document simply carrying no round metadata). ``warnings`` records
        every Milestone 11 recovery performed (a malformed element
        skipped, or duplicate-sequence snapshot events collapsed to one)
        — see the two "Raises" conditions below for what still requires
        fatal, unrecoverable ambiguity.

    Raises:
        RoundResolutionError: If two ``<article-version>`` elements
            resolve to the same ``sequence_number`` but disagree on
            ``article-version-type`` (a genuine, unresolvable ordering
            ambiguity — never guessed, ADR-013). A malformed or missing
            ``vocab-identifier``/``article-version-type`` on an
            individual element no longer raises — see "recovered"
            behavior above; if *every* element is malformed, this
            degrades to the empty-``rounds`` case, not an error (a
            document simply carrying no usable round metadata).
    """
    version_elements = find_all(document.root, "article-version")

    resolved: list[tuple[int, str]] = []
    warnings: list[EngineWarning] = []
    for element in version_elements:
        vocab_identifier = get_attribute(element, "vocab-identifier")
        sequence_number = _extract_sequence_number(vocab_identifier)
        label = get_attribute(element, "article-version-type")
        if sequence_number is None or label is None:
            warnings.append(_build_malformed_version_warning(vocab_identifier, label, article_id))
            continue
        resolved.append((sequence_number, label))

    deduped, dedup_warnings = _dedupe_or_raise(resolved, article_id=article_id)
    warnings.extend(dedup_warnings)

    if not deduped:
        return (), tuple(warnings)

    latest_sequence_number = max(sequence_number for sequence_number, _ in deduped)
    rounds = tuple(
        RoundInfo(
            label=label,
            sequence_number=sequence_number,
            is_latest=(sequence_number == latest_sequence_number),
        )
        for sequence_number, label in sorted(deduped, key=lambda pair: pair[0])
    )
    return rounds, tuple(warnings)


def _dedupe_or_raise(
    resolved: list[tuple[int, str]], *, article_id: str | None
) -> tuple[list[tuple[int, str]], list[EngineWarning]]:
    """Collapse duplicate ``(sequence_number, label)`` snapshot events into one.

    Milestone 11: real production data (bcj-2025-3400) showed 34
    ``<article-version>`` elements sharing one ``sequence_number``, all
    with the identical ``article-version-type`` — confirmed (by
    inspecting every element's ``vocab-identifier`` timestamp) to be
    repeated autosave/snapshot events within the *same* logical round,
    not genuinely distinct rounds. Collapsing identical-label duplicates
    down to one entry is a safe, non-fabricating recovery: it removes
    redundant representations of one round, it does not invent an
    ordering between two *different* rounds. If the same
    ``sequence_number`` carries two different labels, that is a genuine,
    unresolvable ambiguity (ADR-013) and still raises.
    """
    by_sequence: dict[int, set[str]] = {}
    for sequence_number, label in resolved:
        by_sequence.setdefault(sequence_number, set()).add(label)

    conflicting = {seq: labels for seq, labels in by_sequence.items() if len(labels) > 1}
    if conflicting:
        raise RoundResolutionError(
            f"Multiple <article-version> elements resolved to the same "
            f"sequence_number with conflicting labels: {conflicting}",
            article_id=article_id,
            stage=_STAGE,
            rule_id="BR-010",
        )

    duplicate_counts = {
        seq: len([pair for pair in resolved if pair[0] == seq])
        for seq in by_sequence
        if len([pair for pair in resolved if pair[0] == seq]) > 1
    }
    warnings = [
        _build_duplicate_sequence_warning(seq, next(iter(by_sequence[seq])), count, article_id)
        for seq, count in duplicate_counts.items()
    ]
    deduped = [(seq, next(iter(labels))) for seq, labels in by_sequence.items()]
    return deduped, warnings


def _build_malformed_version_warning(
    vocab_identifier: str | None, label: str | None, article_id: str | None
) -> EngineWarning:
    return EngineWarning(
        code=_MALFORMED_VERSION_WARNING_CODE,
        category=WarningCategory.SOURCE_DATA_INCONSISTENCY,
        severity=WarningSeverity.WARNING,
        origin=FindingOrigin.SOURCE_DATA_ISSUE,
        rule_id="BR-010",
        recovery_rule_id=RR_006_MALFORMED_ROUND_SKIPPED.rule_id,
        confidence=ConfidenceLevel.MEDIUM,
        message=(
            f"<article-version> has an unrecognized/missing vocab-identifier "
            f"({vocab_identifier!r}) or article-version-type ({label!r}); "
            f"excluded from the round index ({RR_006_MALFORMED_ROUND_SKIPPED.rule_id}), "
            "package generation continues."
        ),
        article_id=article_id,
        suggested_action="Confirm this <article-version> element's source data upstream.",
        is_recovery=True,
        context=(
            ("vocab_identifier", vocab_identifier or ""),
            ("article_version_type", label or ""),
        ),
    )


def _build_duplicate_sequence_warning(
    sequence_number: int, label: str, count: int, article_id: str | None
) -> EngineWarning:
    return EngineWarning(
        code=_DUPLICATE_SEQUENCE_WARNING_CODE,
        category=WarningCategory.SOURCE_DATA_INCONSISTENCY,
        severity=WarningSeverity.WARNING,
        origin=FindingOrigin.SOURCE_DATA_ISSUE,
        rule_id="BR-010",
        recovery_rule_id=RR_005_DUPLICATE_ROUND_DEDUPED.rule_id,
        confidence=ConfidenceLevel.HIGH,
        message=(
            f"{count} <article-version> elements shared sequence_number "
            f"{sequence_number} and label {label!r} (repeated snapshot events "
            f"of the same round); collapsed to one round index entry "
            f"({RR_005_DUPLICATE_ROUND_DEDUPED.rule_id})."
        ),
        article_id=article_id,
        suggested_action=(
            "No action needed; this reflects repeated autosave events, not distinct rounds."
        ),
        is_recovery=True,
        context=(
            ("sequence_number", str(sequence_number)),
            ("label", label),
            ("duplicate_count", str(count)),
        ),
    )


def _extract_sequence_number(vocab_identifier: str | None) -> int | None:
    if vocab_identifier is None:
        return None
    match = _VOCAB_IDENTIFIER_SEQUENCE_PATTERN.match(vocab_identifier)
    if match is None:
        return None
    return int(match.group(1))
