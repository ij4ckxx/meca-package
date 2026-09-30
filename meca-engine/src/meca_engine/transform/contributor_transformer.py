"""Contributor transformation — Milestone 5B (extended in Milestone 5C).

Builds the ICAM's ordered contributor/affiliation lists from Milestone
4's extracted contributor metadata, plus (Milestone 5C) reviewer and
copy-editor identity sourced from the already-classified
`CustomMetaStore`. Per 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §3.3:
`Contributor`/`Affiliation` are linked by model-internal integer keys
assigned here at build time, never by the source's own affiliation
element id — those source ids never appear anywhere in the ICAM.

**Author mapping is unchanged from Milestone 5B** — the same fields,
same order, same corresponding-email logic. This is purely additive.

**Reviewer/Copy-Editor mapping (Milestone 5C, Architecture Review §2.5)**:
sourced from `CustomMetaStore.reviewer_scorecards`/`.decline_reasons`
(reviewers) and two specific `FormAnswerBag` keys, `"copyeditor assigned
by"`/`"copyeditor information"` (copy editors) — both confirmed present
in real reference-package data. Reviewer identity is not split into
surname/given-names (the source gives one flattened name string per
scorecard/decline entry) — preserved verbatim in
`Contributor.full_name_raw` rather than guessed at a split, **unless**
a structured `<contrib contrib-type="reviewer">` record also exists
directly in `<contrib-group>` (Milestone 9: `bcj-2025-3130` is the first
observed package where this is the case) — see
`_structured_reviewer_lookup`. When one matches by name or email, its
real surname/given-names/orcid/affiliation are used instead of the
flattened string, which also lets the reviewer's own
`<xref ref-type="aff">` be resolved like an author's. This correction
originally applied to `raw_xml`/`article_xml` output only — until
BR-163 (Business Rule Completion milestone), which extended the same,
already-computed structured-identity result to reviews.xml too (see
`generators/reviews_xml/review_builder.py`'s `build_structured_reviewer_lookup`)
whenever a scorecard/decline reviewer's name or email matches; every
non-matching reviewer's `<string-name>` is unaffected. The same
reviewer can appear in more than one round's scorecard; this
transformer deduplicates by a case-insensitive, whitespace-trimmed name
key, in first-encountered document order, keeping the first non-empty
email found for that name across all their scorecard/decline entries.
Copy-editor identity: the source `<meta-value>` for both confirmed keys
holds an `<email>` and a `<user-name>` child element side by side, but
Milestone 4's custom-meta extraction only captures `<named-content>`
children structurally — everything else (this included) flattens into
one concatenated `value_text` string with no separator (e.g.
`"gyanabati.l@kriyadocs.comGyanabati L"`). Rather than extend the
extraction layer's schema for what is currently only these two known
keys, this transformer splits that single string back into email/name
with a generic email-shaped regex — a structural pattern match on
already-extracted text, not a business-semantic guess (the same class of
operation as trimming whitespace). The regex bounds the TLD to a run of
lowercase letters (real emails here are lowercase) so it stops at the
name text immediately following, rather than a naive greedy match
consuming into it.

**Editor/associate-editor mapping (Milestone 9)**: Milestone 5C found
`editor`/`associate-editor` `contrib-type` values directly inside
`<contrib-group>` elements (`ContributorMetadata.editors`, after
Milestone 9's extraction-layer correction — see
`contributor_metadata_extractor`'s own note) but left them unmapped
pending 3 business questions. Approved minimal-scope resolution:
(1) the generic `"editor"` string (no BR/ADR names which specific
Handling/Academic/Guest/Production Editor role it represents) maps to
`ContribType.OTHER` — the enum's own documented escape hatch — with the
verbatim string preserved via `raw_contrib_type`, rather than guessing
a specific member; `"associate-editor"` maps exactly, since that member
already exists. (2) The same person repeated across sibling
`<contrib-group>` snapshots is deduped by case-insensitive,
whitespace-trimmed name in first-seen order — the same pattern already
used for reviewers. (3) The `"reviewer"` vs. `"suggested-reviewer"`
distinction remains genuinely out of scope — no field carries it at the
per-contrib level, and this correction does not touch reviewer mapping.
See `_build_editor_contributors`.

**Corresponding-email resolution (BR-130)**: unchanged from Milestone 5B
— collects every author's email where `is_corresponding=True`, in author
(document) order; index 0 becomes the primary corresponding email.

**Institution fallback, evidence-based**: falls back to
`AffiliationRecord.raw_text` only when neither `.institution` nor
`.department` was recognized; when both are present they're joined as
`"<department>, <institution>"`, matching real reference-package style
(Milestone 9 affiliation-structure correction). `.city`/`.state` pass
through separately rather than being folded into `.institution`.

A dangling `affiliation_keys` reference (a source `ref-id` that names no
known affiliation) is logged as a warning and omitted from the
contributor's `affiliation_keys` — never included, since an included but
dangling key would make `model.validation`'s structural check fail for a
condition this transformer could have avoided by simply not asserting a
reference it could not resolve.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from meca_engine.model.article import Affiliation, Contributor, CorrespEmail, FormAnswerBag
from meca_engine.model.enums import ContribType

if TYPE_CHECKING:
    from meca_engine.extraction.metadata_models import ContributorMetadata, ContributorRecord
    from meca_engine.logging_.structured_logger import StructuredLogger
    from meca_engine.model.article import DeclineReason, ReviewerScorecard

_STAGE = "transform.contributor_transformer"
_COPYEDITOR_FORM_ANSWER_KEYS = ("copyeditor assigned by", "copyeditor information")
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}")


def build_contributors_and_affiliations(
    contributor_metadata: ContributorMetadata,
    *,
    reviewer_scorecards: tuple[ReviewerScorecard, ...] = (),
    decline_reasons: tuple[DeclineReason, ...] = (),
    form_answers: FormAnswerBag | None = None,
    logger: StructuredLogger | None = None,
) -> tuple[tuple[Contributor, ...], tuple[Affiliation, ...], tuple[CorrespEmail, ...]]:
    """Build the article's ordered contributors, affiliations, and corresponding emails.

    Args:
        contributor_metadata: Milestone 4's extracted contributor metadata.
        reviewer_scorecards: The classified `CustomMetaStore`'s reviewer
            scorecards, if available — used to populate reviewer-role
            contributors (Milestone 5C). Defaults to empty for callers
            that predate this parameter.
        decline_reasons: The classified `CustomMetaStore`'s decline
            reasons, if available — used the same way, for reviewers who
            declined rather than completed a review.
        form_answers: The classified `CustomMetaStore`'s form answers, if
            available — used to populate copy-editor-role contributors.
        logger: Optional structured logger; logs one warning per dangling
            affiliation reference encountered.

    Returns:
        A ``(contributors, affiliations, corresponding_emails)`` tuple,
        each element itself a tuple, in document order (authors, then
        reviewers, then copy editors).
    """
    affiliations: list[Affiliation] = []
    model_key_by_element_id: dict[str, int] = {}
    for index, affiliation_record in enumerate(contributor_metadata.affiliations, start=1):
        institution = affiliation_record.institution
        if institution is not None and affiliation_record.department is not None:
            institution = f"{affiliation_record.department}, {institution}"
        elif institution is None:
            institution = affiliation_record.department
        affiliations.append(
            Affiliation(
                model_key=index,
                institution=institution or affiliation_record.raw_text,
                label=affiliation_record.label,
                city=affiliation_record.city,
                state=affiliation_record.state,
                country=affiliation_record.country,
            )
        )
        if affiliation_record.element_id is not None:
            model_key_by_element_id[affiliation_record.element_id] = index

    contributors: list[Contributor] = []
    corresponding_emails: list[CorrespEmail] = []
    for author_record in contributor_metadata.authors:
        affiliation_keys: list[int] = []
        for ref_id in author_record.affiliation_ref_ids:
            model_key = model_key_by_element_id.get(ref_id)
            if model_key is None:
                if logger is not None:
                    logger.warn(
                        "Contributor references an unresolvable affiliation id",
                        stage=_STAGE,
                        context={"surname": author_record.surname, "affiliation_ref_id": ref_id},
                    )
                continue
            affiliation_keys.append(model_key)

        contributors.append(
            Contributor(
                surname=author_record.surname or "",
                given_names=author_record.given_names or "",
                contrib_type=ContribType.AUTHOR,
                email=author_record.emails[0] if author_record.emails else None,
                orcid=author_record.orcid,
                affiliation_keys=tuple(affiliation_keys),
                is_corresponding=author_record.is_corresponding,
                is_submitting_author=author_record.is_submitting_author,
            )
        )
        if author_record.is_corresponding and author_record.emails:
            corresponding_emails.append(CorrespEmail(email=author_record.emails[0]))

    contributors.extend(_build_editor_contributors(contributor_metadata.editors))
    contributors.extend(
        _build_reviewer_contributors(
            reviewer_scorecards,
            decline_reasons,
            contributor_metadata.other_contributors,
            model_key_by_element_id,
            logger,
        )
    )
    contributors.extend(_build_copy_editor_contributors(form_answers))

    return tuple(contributors), tuple(affiliations), tuple(corresponding_emails)


_EDITOR_CONTRIB_TYPE_BY_RAW = {"associate-editor": ContribType.ASSOCIATE_EDITOR}


def _build_editor_contributors(
    editor_records: tuple[ContributorRecord, ...],
) -> tuple[Contributor, ...]:
    """Milestone 9: minimal literal mapping for `editor`/`associate-editor` contrib-types.

    Previously dropped entirely pending 3 open business questions (see
    module docstring history). Approved minimal scope: `"editor"` (a
    generic, undifferentiated source string — no BR/ADR names which
    specific editor role it represents) maps to the enum's own
    documented escape hatch, `ContribType.OTHER`, with the verbatim
    source string preserved via `raw_contrib_type` so no information is
    lost even though it collapses to `OTHER`; `"associate-editor"` maps
    exactly, since that member already exists. Deduped by
    case-insensitive, whitespace-trimmed name in first-seen order, same
    pattern as `_build_reviewer_contributors` — the "same person
    repeated across sibling snapshots" question this resolves; the
    "reviewer vs. suggested-reviewer" question remains genuinely out of
    scope (no field carries it).
    """
    order: list[str] = []
    by_key: dict[str, ContributorRecord] = {}
    for record in editor_records:
        key = f"{record.surname or ''} {record.given_names or ''}".strip().lower()
        if not key:
            continue
        if key not in by_key:
            order.append(key)
            by_key[key] = record

    return tuple(
        Contributor(
            surname=by_key[key].surname or "",
            given_names=by_key[key].given_names or "",
            contrib_type=_EDITOR_CONTRIB_TYPE_BY_RAW.get(
                by_key[key].contrib_type or "", ContribType.OTHER
            ),
            email=by_key[key].emails[0] if by_key[key].emails else None,
            orcid=by_key[key].orcid,
            raw_contrib_type=by_key[key].contrib_type,
        )
        for key in order
    )


def _structured_reviewer_lookup(
    other_contributors: tuple[ContributorRecord, ...],
) -> dict[str, ContributorRecord]:
    """Milestone 9: index structured `<contrib contrib-type="reviewer">` records.

    Keyed by every normalized (lower-cased, whitespace-trimmed) full-name
    ordering and email a scorecard/decline entry's flattened name or
    email might match against — best-effort overlap, not an exact-schema
    join (no shared source id exists between the two data shapes).
    """
    lookup: dict[str, ContributorRecord] = {}
    for record in other_contributors:
        if record.contrib_type != "reviewer":
            continue
        surname = (record.surname or "").strip()
        given_names = (record.given_names or "").strip()
        if surname and given_names:
            lookup.setdefault(f"{given_names} {surname}".lower(), record)
            lookup.setdefault(f"{surname} {given_names}".lower(), record)
        for email in record.emails:
            lookup.setdefault(email.strip().lower(), record)
    return lookup


def _resolve_affiliation_keys(
    record: ContributorRecord,
    model_key_by_element_id: dict[str, int] | None,
    logger: StructuredLogger | None,
) -> tuple[int, ...]:
    if model_key_by_element_id is None:
        return ()
    keys: list[int] = []
    for ref_id in record.affiliation_ref_ids:
        model_key = model_key_by_element_id.get(ref_id)
        if model_key is None:
            if logger is not None:
                logger.warn(
                    "Contributor references an unresolvable affiliation id",
                    stage=_STAGE,
                    context={"surname": record.surname, "affiliation_ref_id": ref_id},
                )
            continue
        keys.append(model_key)
    return tuple(keys)


def _find_structured_reviewer_match(
    structured: dict[str, ContributorRecord], name_key: str, email: str | None
) -> ContributorRecord | None:
    match = structured.get(name_key)
    if match is not None or email is None:
        return match
    return structured.get(email.strip().lower())


def _new_reviewer_contributor(
    name: str,
    email: str | None,
    structured: dict[str, ContributorRecord],
    name_key: str,
    model_key_by_element_id: dict[str, int] | None,
    logger: StructuredLogger | None,
) -> Contributor:
    match = _find_structured_reviewer_match(structured, name_key, email)
    if match is None:
        return Contributor(
            surname="",
            given_names="",
            contrib_type=ContribType.REVIEWER,
            email=email,
            full_name_raw=name,
            raw_contrib_type="reviewer",
        )
    # Structured source data available — use it instead of the flattened
    # scorecard/decline string (Milestone 9).
    return Contributor(
        surname=match.surname or "",
        given_names=match.given_names or "",
        contrib_type=ContribType.REVIEWER,
        email=email or (match.emails[0] if match.emails else None),
        orcid=match.orcid,
        affiliation_keys=_resolve_affiliation_keys(match, model_key_by_element_id, logger),
        raw_contrib_type="reviewer",
    )


def _build_reviewer_contributors(
    reviewer_scorecards: tuple[ReviewerScorecard, ...],
    decline_reasons: tuple[DeclineReason, ...],
    other_contributors: tuple[ContributorRecord, ...] = (),
    model_key_by_element_id: dict[str, int] | None = None,
    logger: StructuredLogger | None = None,
) -> tuple[Contributor, ...]:
    order: list[str] = []
    by_key: dict[str, Contributor] = {}
    structured = _structured_reviewer_lookup(other_contributors)

    def _add(name: str, email: str | None) -> None:
        key = name.strip().lower()
        if not key:
            return
        existing = by_key.get(key)
        if existing is None:
            order.append(key)
            by_key[key] = _new_reviewer_contributor(
                name, email, structured, key, model_key_by_element_id, logger
            )
        elif existing.email is None and email is not None:
            by_key[key] = Contributor(
                surname=existing.surname,
                given_names=existing.given_names,
                contrib_type=existing.contrib_type,
                email=email,
                full_name_raw=existing.full_name_raw,
                raw_contrib_type=existing.raw_contrib_type,
            )

    for scorecard in reviewer_scorecards:
        _add(scorecard.reviewer_name, scorecard.reviewer_email or None)
    for decline_reason in decline_reasons:
        _add(decline_reason.reviewer_name, None)

    return tuple(by_key[key] for key in order)


def _split_email_and_name(text: str) -> tuple[str | None, str | None]:
    match = _EMAIL_PATTERN.search(text)
    if match is None:
        return None, text.strip() or None
    email = match.group(0)
    name = (text[: match.start()] + text[match.end() :]).strip()
    return email, name or None


def _build_copy_editor_contributors(form_answers: FormAnswerBag | None) -> tuple[Contributor, ...]:
    if form_answers is None:
        return ()
    contributors: list[Contributor] = []
    for key in _COPYEDITOR_FORM_ANSWER_KEYS:
        for value in form_answers.get(key) or ():
            email, name = _split_email_and_name(value)
            if email is None and name is None:
                continue
            contributors.append(
                Contributor(
                    surname="",
                    given_names="",
                    contrib_type=ContribType.COPY_EDITOR,
                    email=email,
                    full_name_raw=name,
                    raw_contrib_type=key,
                )
            )
    return tuple(contributors)
