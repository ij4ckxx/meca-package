"""Recovery Rule catalog — Milestone 12 (Archive Migration Engine).

A **Recovery Rule** describes how the engine proceeds when a Business
Rule (`01_BUSINESS_RULE_BOOK.md`) cannot be fully satisfied by the
source data, without fabricating anything. Business Rules describe the
*ideal* output; Recovery Rules describe the *fallback* the engine takes
when that ideal cannot be reached, and are a deliberately separate
catalog — never mixed into the Business Rule Book itself.

Every recovery the engine performs is tagged with exactly one rule ID
from this catalog (via `EngineWarning.recovery_rule_id`), so a
Conversion Report can state precisely which fallback fired, not just
that "something was recovered."

Constraints every Recovery Rule must honor (enforced by review, not by
this module): never fabricate information, never modify source files,
never apply silently (every application creates a warning), and never
proceed if doing so would produce a technically invalid MECA package.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryRule:
    """One entry in the Recovery Rule catalog."""

    rule_id: str
    name: str
    description: str


RR_001_FILENAME_FROM_PATH = RecoveryRule(
    rule_id="RR-001",
    name="Filename recovered from path basename",
    description=(
        "A declared file's name was empty but its declared path was usable; the "
        "filename is derived from the path's basename for generation purposes only "
        "(extraction/file_resolver.py)."
    ),
)

RR_002_MISSING_FILE_SKIPPED = RecoveryRule(
    rule_id="RR-002",
    name="Missing supporting file skipped",
    description=(
        "A declared, non-manuscript file (e.g. a license form, cover letter, or "
        "figure) had no matching physical file anywhere in the staged submission; "
        "the entry is skipped and the package is generated without it "
        "(extraction/file_resolver.py). The manuscript file itself is never "
        "skipped — see FATAL_FAILURE."
    ),
)

RR_003_REVIEWER_IDENTITY_OMITTED = RecoveryRule(
    rule_id="RR-003",
    name="Missing reviewer identity omitted",
    description=(
        "A reviewer scorecard has real recommendation/comment content but no "
        "name or email; the content is kept and the identity is omitted "
        "(generators/reviews_xml/review_builder.py)."
    ),
)

RR_004_TOLERANT_FILE_MATCH = RecoveryRule(
    rule_id="RR-004",
    name="File resolved via filename tolerance matching",
    description=(
        "A declared filename was resolved to a physical file via a non-exact "
        "match (stem-only, prefix, or whitespace/underscore-normalized) rather "
        "than a literal name match (extraction/file_resolver.py)."
    ),
)

RR_005_DUPLICATE_ROUND_DEDUPED = RecoveryRule(
    rule_id="RR-005",
    name="Duplicate round-version snapshot deduplicated",
    description=(
        "Multiple <article-version> elements shared the same sequence number and "
        "label (repeated autosave/snapshot events of one round); collapsed to a "
        "single round index entry (extraction/round_resolver.py)."
    ),
)

RR_006_MALFORMED_ROUND_SKIPPED = RecoveryRule(
    rule_id="RR-006",
    name="Malformed round-version metadata skipped",
    description=(
        "An <article-version> element had an unrecognized/missing vocab-identifier "
        "or article-version-type; excluded from the round index rather than "
        "failing resolution for every round (extraction/round_resolver.py)."
    ),
)

RR_007_OPTIONAL_SECTION_OMITTED = RecoveryRule(
    rule_id="RR-007",
    name="Optional XML section omitted",
    description=(
        "An optional article.xml section could not be populated from a "
        "configuration or source gap (e.g. no license template configured for a "
        "resolved License Type); the section is omitted rather than fabricated "
        "(generators/article_xml/generator.py)."
    ),
)

ALL_RECOVERY_RULES: tuple[RecoveryRule, ...] = (
    RR_001_FILENAME_FROM_PATH,
    RR_002_MISSING_FILE_SKIPPED,
    RR_003_REVIEWER_IDENTITY_OMITTED,
    RR_004_TOLERANT_FILE_MATCH,
    RR_005_DUPLICATE_ROUND_DEDUPED,
    RR_006_MALFORMED_ROUND_SKIPPED,
    RR_007_OPTIONAL_SECTION_OMITTED,
)

# Recovery rules whose application means real, declared content is absent
# from the generated package (as opposed to content that was simply
# located/ordered/derived differently) — the signal `PackageBuilder` uses
# to distinguish `PARTIAL_CERTIFICATION` from `CERTIFIED_WITH_RECOVERY`.
SIGNIFICANT_DEFICIENCY_RULE_IDS: frozenset[str] = frozenset({RR_002_MISSING_FILE_SKIPPED.rule_id})
