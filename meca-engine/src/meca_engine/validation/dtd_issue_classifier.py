"""Specification-alignment classification for remaining DTD findings.

Every DTD finding this engine can currently produce was individually
investigated against the real corpus (see `DTD_Fix_Summary.md` and
`Remaining_Validation_Issues.md`) and classified into exactly one of
the categories below. This module is a lookup over those *specific,
already-catalogued* message patterns — never a generic heuristic — so
an uncatalogued DTD message (one this investigation never saw) is
classified ``VALIDATION_ONLY`` by default: the safe, "don't assume
this is fine" fallback, not an unearned "safe to fix" or "safe to
recommend" label.
"""

from __future__ import annotations

import re
from enum import Enum, unique


@unique
class SpecAlignmentCategory(str, Enum):
    """Where one remaining DTD finding sits in the spec-alignment classification."""

    SOURCE_DATA_ISSUE = "source_data_issue"
    BUSINESS_RULE_CANDIDATE = "business_rule_candidate"
    RECOVERY_RULE_CANDIDATE = "recovery_rule_candidate"
    VALIDATION_ONLY = "validation_only"


# Ordered (first match wins) (compiled pattern, category) pairs. Every
# pattern here traces to a specific, named finding in
# `DTD_Fix_Summary.md` / `Remaining_Validation_Issues.md` — see those
# documents for the full investigation and reasoning behind each one.
_PATTERNS: tuple[tuple[re.Pattern[str], SpecAlignmentCategory], ...] = (
    # BR-161/162 (Business Rule Completion milestone) now fix data-type
    # and comma-separated xref/@rid corpus-wide at generation time — these
    # 3 patterns should no longer occur. Kept only as a safety net: if one
    # ever does (e.g. a shape this corpus never exercised), it falls
    # through to the VALIDATION_ONLY default below rather than being
    # silently mis-classified as still-pending.
    #
    # BR-163 resolves reviews.xml's <string-name> whenever a matching
    # structured reviewer identity exists elsewhere in the same source
    # document (partial coverage by nature — see BR-163's Business Rule
    # Book entry). A remaining <string-name>/name-alternatives finding
    # now means no such match exists — inventing a name split would be
    # fabrication, so these are Validation Only, not a pending Business
    # Rule (the rule that would have fixed them is already implemented).
    (
        re.compile(r"No declaration for element string-name"),
        SpecAlignmentCategory.VALIDATION_ONLY,
    ),
    (
        re.compile(r"Element contrib content does not follow the DTD.*name-alternatives"),
        SpecAlignmentCategory.VALIDATION_ONLY,
    ),
    # Duplicate ids (aff/cor/con...) where the repeats carry genuinely
    # different content (confirmed per-article, e.g. aff: different
    # institution text under one id; con: the same CRediT role code
    # reused with different role text across separate editorial rounds
    # in the source, promoted to a literal XML id by raw_xml's own
    # cleanup XSLT) — the source itself is self-contradictory; no safe,
    # lossless resolution exists without a policy decision on how to
    # disambiguate/renumber (any rename risks silently re-pointing an
    # xref at the wrong repeat, since the xrefs are indistinguishable in
    # source). Prefix-agnostic on purpose: this reasoning holds for any
    # id, not just the two prefixes first observed.
    (
        re.compile(r"^ID \S+ already defined"),
        SpecAlignmentCategory.SOURCE_DATA_ISSUE,
    ),
    # Everything below requires inventing data, changing semantics, or
    # assuming an attribute/structure is safe to alter — validation-only.
    (
        re.compile(r"Element fn content does not follow the DTD"),
        SpecAlignmentCategory.VALIDATION_ONLY,
    ),
    (
        re.compile(r"No declaration for attribute target of element ext-link"),
        SpecAlignmentCategory.VALIDATION_ONLY,
    ),
    (
        re.compile(r"No declaration for attribute dir of element p\b"),
        SpecAlignmentCategory.VALIDATION_ONLY,
    ),
    (
        re.compile(r"No declaration for attribute award-id-type"),
        SpecAlignmentCategory.VALIDATION_ONLY,
    ),
)


def classify_dtd_issue(message: str) -> SpecAlignmentCategory:
    """Classify one DTD finding's message into a spec-alignment category.

    Falls back to :attr:`SpecAlignmentCategory.VALIDATION_ONLY` for any
    message this investigation hasn't specifically catalogued — an
    unrecognized finding is never assumed safe to fix or recommend.
    """
    for pattern, category in _PATTERNS:
        if pattern.search(message):
            return category
    return SpecAlignmentCategory.VALIDATION_ONLY
