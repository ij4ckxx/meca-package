"""Review-block construction — one ``<review review-type="review">`` per (reviewer × round).

BR-102/106/107/112/125. See ``generator.py``'s module docstring for the
full BR/ADR traceability and `26_REVIEWS_DECISION_LOG.md` for every
judgment call this module makes (in particular: why BR-103/104/108/111's
richer recommendation/comments/file/multi-point-split content is never
attempted — no ICAM field carries it on any of the 3 real reference
packages today).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.generators.xml.helpers import add_optional_element
from meca_engine.model.enums import CorrespondenceKind, ReviewOutcomeStatus

if TYPE_CHECKING:
    from collections.abc import Mapping
    from xml.etree.ElementTree import Element

    from meca_engine.config.schema import FeatureFlagsConfig, ReviewsXmlConfig
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.xml.builder import XmlDocumentBuilder
    from meca_engine.model.article import DeclineReason, ReviewerScorecard, WorkflowLog
    from meca_engine.model.collections import ContributorList

    # BR-163: name-key/email-key -> (surname, given_names), built once per
    # article by `build_structured_reviewer_lookup` from the already-built,
    # already-correlated `ArticleModel.article_meta.contributors` (see that
    # function's docstring).
    StructuredReviewerLookup = Mapping[str, tuple[str, str]]

_GENERATOR_NAME = "reviews_xml"
_REVIEW_TYPE = "review"
_EXTENDED_SCOPE_KINDS = frozenset(
    {
        CorrespondenceKind.SCREENING_QUERY,
        CorrespondenceKind.EDITOR_REASSIGNMENT,
        CorrespondenceKind.AUTHOR_SUGGESTED_REVIEWER,
        CorrespondenceKind.PRODUCTION_QUERY,
    }
)


def build_scorecard_reviews(
    builder: XmlDocumentBuilder,
    config: ReviewsXmlConfig,
    scorecards: tuple[ReviewerScorecard, ...],
    diagnostics: DiagnosticsCollector,
    structured_lookup: StructuredReviewerLookup | None = None,
) -> tuple[Element, ...]:
    """BR-102/103/104/112: one review-type="review" block per completed scorecard.

    Only the ``QN_*`` answers (``ReviewerScorecard.answers``) are real,
    populated content on any of the 3 real reference packages —
    ``overall_recommendation`` and every date field are always ``None``
    (confirmed 3/3; see the Reviews Decision Log). BR-103/104's
    recommendation/comments split is therefore diagnosed as unavailable,
    never fabricated, and no ``<date>`` element is ever emitted.
    """
    reviews: list[Element] = []
    for scorecard in scorecards:
        if scorecard.outcome_status is not ReviewOutcomeStatus.COMPLETED:
            diagnostics.info(
                _GENERATOR_NAME,
                f"Reviewer scorecard for {scorecard.reviewer_name!r} (round "
                f"{scorecard.round_label!r}) has outcome_status "
                f"{scorecard.outcome_status.value!r}, not 'completed'; rendering "
                f"as a status-only review per BR-106",
            )
            reviews.append(
                _build_status_only_review(
                    builder,
                    config,
                    round_label=scorecard.round_label,
                    reviewer_name=scorecard.reviewer_name,
                    reviewer_email=scorecard.reviewer_email,
                    status_text=scorecard.outcome_status.value,
                    structured_lookup=structured_lookup,
                    diagnostics=diagnostics,
                )
            )
            continue

        _require_reviewer_identity(scorecard, diagnostics)
        if not scorecard.overall_recommendation:
            diagnostics.info(
                _GENERATOR_NAME,
                f"No overall_recommendation available for {scorecard.reviewer_name!r} "
                f"(round {scorecard.round_label!r}) — BR-103's recommendation "
                f"review-item is not emitted (ICAM gap, not fabricated)",
            )
        if not scorecard.answers:
            diagnostics.warn(
                _GENERATOR_NAME,
                f"Reviewer scorecard for {scorecard.reviewer_name!r} (round "
                f"{scorecard.round_label!r}) is marked completed but has no answers",
            )

        review = builder.create_root(
            "review",
            attributes={
                "review-version": scorecard.round_label,
                "review-type": _REVIEW_TYPE,
                "blinding": config.blinding,
                "permission-to-publish": config.permission_to_publish,
                "permission-to-transfer": config.permission_to_transfer,
            },
        )
        item_group = builder.create_element(review, "review-item-group")
        add_review_item(
            builder,
            item_group,
            item_type="comments",
            title=config.scorecard_review_item_title,
            data=_format_answers(scorecard.answers),
            data_type=config.review_item_data_type,
        )
        add_reviews_contrib(
            builder,
            review,
            "reviewer",
            scorecard.reviewer_name,
            scorecard.reviewer_email,
            structured_lookup=structured_lookup,
            diagnostics=diagnostics,
        )
        reviews.append(review)
    return tuple(reviews)


def build_decline_reviews(
    builder: XmlDocumentBuilder,
    config: ReviewsXmlConfig,
    decline_reasons: tuple[DeclineReason, ...],
    diagnostics: DiagnosticsCollector,
    structured_lookup: StructuredReviewerLookup | None = None,
) -> tuple[Element, ...]:
    """BR-106/107/125: one status-only review-type="review" block per declined/terminated reviewer.

    ``DeclineReason`` carries no separate declined-vs-terminated status
    field (only free-text ``reason_text``) — the status wording used
    here is that verbatim text, never a synthesized enum string like
    "Terminated - Auto Unassigned" (BR-107 warns against hard-coding one
    literal; this generator goes further and never guesses which
    category applies at all).
    """
    reviews: list[Element] = []
    for decline in decline_reasons:
        if not decline.reviewer_name:
            diagnostics.warn(
                _GENERATOR_NAME,
                f"Decline reason for round {decline.round_label!r} has no reviewer name",
            )
        reviews.append(
            _build_status_only_review(
                builder,
                config,
                round_label=decline.round_label,
                reviewer_name=decline.reviewer_name,
                reviewer_email="",
                status_text=decline.reason_text,
                structured_lookup=structured_lookup,
                diagnostics=diagnostics,
            )
        )
    return tuple(reviews)


def build_extended_history_reviews(
    builder: XmlDocumentBuilder,
    config: ReviewsXmlConfig,
    feature_flags: FeatureFlagsConfig,
    workflow_log: WorkflowLog,
    diagnostics: DiagnosticsCollector,
) -> tuple[Element, ...]:
    """ADR-004/BR-116 duplicate correspondence + ADR-005/BR-111/117-119 extended scope.

    Both categories are entirely sourced from ``WorkflowLog.events`` —
    confirmed empty (0 events) on all 3 real reference packages today,
    so this function never produces output against real data; it exists
    so the generator is ready the moment a future extraction-layer
    milestone populates ``WorkflowLog`` (see the Reviews Decision Log),
    and is exercised by synthetic fixtures per the same precedent
    ADR-013 already established for un-evidenced-but-approved paths.
    """
    reviews: list[Element] = []
    for event in workflow_log.events:
        if event.event_kind is CorrespondenceKind.REVIEW_COMMENT:
            if not feature_flags.reviews_include_duplicate_correspondence:
                continue
            title = config.duplicate_correspondence_review_item_title
        elif event.event_kind in _EXTENDED_SCOPE_KINDS:
            if not feature_flags.reviews_extended_history_scope:
                continue
            title = config.extended_history_review_item_title
        else:
            diagnostics.warn(
                _GENERATOR_NAME,
                f"Correspondence event has unsupported event_kind "
                f"{event.event_kind.value!r}; skipped",
            )
            continue

        review = builder.create_root(
            "review",
            attributes={
                "review-version": event.round_label or "",
                "review-type": _REVIEW_TYPE,
                "blinding": config.blinding,
                "permission-to-publish": config.permission_to_publish,
                "permission-to-transfer": config.permission_to_transfer,
            },
        )
        item_group = builder.create_element(review, "review-item-group")
        item = add_review_item(
            builder,
            item_group,
            item_type="correspondence",
            title=title,
            data=event.text,
            data_type=config.review_item_data_type,
        )
        if event.attachment_url:  # BR-108
            builder.create_element(
                item, "ext-link", attributes={"xlink:href": event.attachment_url}
            )
        add_reviews_contrib(builder, review, "reviewer", event.actor_name, "")
        reviews.append(review)
    return tuple(reviews)


def _require_reviewer_identity(
    scorecard: ReviewerScorecard, diagnostics: DiagnosticsCollector
) -> None:
    if scorecard.reviewer_name or scorecard.reviewer_email:
        return
    if scorecard.overall_recommendation:
        # Milestone 11 (Recovery + Warning framework): the review content
        # itself (recommendation/comments) is real, source-derived data —
        # only the identity attribution is missing. Discarding real
        # review content over a missing name is disproportionate;
        # generation continues with the identity omitted (already a
        # tolerated shape elsewhere — editor/associate-editor contribs
        # are routinely absent, see production_validation/04's BR-113
        # finding) and a warning instead of a raised exception.
        diagnostics.warn(
            _GENERATOR_NAME,
            f"Reviewer scorecard for round {scorecard.round_label!r} has a "
            "recommendation but no reviewer identity; recommendation included, "
            "identity omitted (recoverable, BR-112, RR-003)",
        )
        return
    diagnostics.warn(
        _GENERATOR_NAME, f"Reviewer scorecard for round {scorecard.round_label!r} has no name/email"
    )


def _build_status_only_review(
    builder: XmlDocumentBuilder,
    config: ReviewsXmlConfig,
    *,
    round_label: str,
    reviewer_name: str,
    reviewer_email: str,
    status_text: str,
    structured_lookup: StructuredReviewerLookup | None = None,
    diagnostics: DiagnosticsCollector | None = None,
) -> Element:
    review = builder.create_root(
        "review",
        attributes={
            "review-version": round_label,
            "review-type": _REVIEW_TYPE,
            "blinding": config.blinding,
            "permission-to-publish": config.permission_to_publish,
            "permission-to-transfer": config.permission_to_transfer,
        },
    )
    item_group = builder.create_element(review, "review-item-group")
    add_review_item(
        builder,
        item_group,
        item_type="correspondence",
        title=config.decline_review_item_title,
        data=status_text,
        data_type=config.review_item_data_type,
    )
    add_reviews_contrib(
        builder,
        review,
        "reviewer",
        reviewer_name,
        reviewer_email,
        structured_lookup=structured_lookup,
        diagnostics=diagnostics,
    )
    return review


def add_review_item(
    builder: XmlDocumentBuilder,
    item_group: Element,
    *,
    item_type: str,
    title: str,
    data: str,
    data_type: str,
) -> Element:
    """Append one ``<review-item>`` (question/title + response/data), shared by both builders."""
    item = builder.create_element(
        item_group, "review-item", attributes={"review-item-type": item_type}
    )
    question = builder.create_element(item, "review-item-question")
    builder.create_element(question, "title", text=title)
    response = builder.create_element(item, "review-item-response")
    builder.create_element(
        response, "review-item-data", attributes={"review-item-data-type": data_type}, text=data
    )
    return item


def build_structured_reviewer_lookup(contributors: ContributorList) -> StructuredReviewerLookup:
    """BR-163: index already-correlated reviewer identities for reviews.xml's use.

    `transform/contributor_transformer.py`'s `_build_reviewer_contributors`
    already matches each scorecard/decline reviewer's flattened name/email
    against a structured ``<contrib contrib-type="reviewer">`` record
    elsewhere in the same source document, when one exists, and builds a
    proper ``Contributor(surname=..., given_names=...)`` for article.xml.
    This reuses that same, already-computed result — no new correlation
    logic, no re-reading of source XML — so reviews.xml can emit the
    identical structured name reviews.xml's own flattened scorecard would
    otherwise never resolve on its own (BR-113's isolation from
    `ArticleMeta.contributors` is not bypassed for the *content* it
    builds; only this narrow, evidence-backed identity lookup is shared).

    Keyed the same way name/email might arrive at a call site
    (case-insensitive, whitespace-trimmed name in either order, or
    email), mirroring `_structured_reviewer_lookup`'s own indexing.
    Corpus-wide coverage is partial by nature (only 13/37 articles in
    the DTD-compliance corpus have a matching structured record at all)
    — every unmatched name falls back to `<string-name>`, unchanged.
    """
    lookup: dict[str, tuple[str, str]] = {}
    for contributor in contributors:
        if contributor.raw_contrib_type != "reviewer":
            continue
        surname = (contributor.surname or "").strip()
        given_names = (contributor.given_names or "").strip()
        if not surname or not given_names:
            continue
        structured = (surname, given_names)
        lookup.setdefault(f"{given_names} {surname}".lower(), structured)
        lookup.setdefault(f"{surname} {given_names}".lower(), structured)
        if contributor.email:
            lookup.setdefault(contributor.email.strip().lower(), structured)
    return lookup


def _find_structured_name(
    lookup: StructuredReviewerLookup, name: str, email: str
) -> tuple[str, str] | None:
    match = lookup.get(name.strip().lower())
    if match is not None or not email:
        return match
    return lookup.get(email.strip().lower())


def add_reviews_contrib(
    builder: XmlDocumentBuilder,
    review: Element,
    contrib_type: str,
    name: str,
    email: str,
    *,
    structured_lookup: StructuredReviewerLookup | None = None,
    diagnostics: DiagnosticsCollector | None = None,
) -> None:
    """Append one ``<contrib-group>`` (BR-112/113), shared by both builders.

    Uses ``<string-name>`` (an unsplit, raw name string) by default —
    `ReviewerScorecard`/`DeclineReason`/`DecisionDraft` all carry only a
    single raw name string, never pre-split components, so splitting one
    here would require inventing name-parsing logic never evidenced or
    approved. BR-163: when ``structured_lookup`` is given (only passed
    for ``contrib_type == "reviewer"``) and ``name``/``email`` matches an
    already-correlated structured identity, emits ``<name><surname>/
    <given-names></name>`` instead — no fabrication, since the matched
    surname/given-names come from a real, structured record already
    present in the same source document.
    """
    contrib = builder.create_element(review, "contrib-group")
    person = builder.create_element(contrib, "contrib", attributes={"contrib-type": contrib_type})
    structured = (
        _find_structured_name(structured_lookup, name, email) if structured_lookup else None
    )
    if structured is not None:
        surname, given_names = structured
        name_element = builder.create_element(person, "name")
        add_optional_element(builder, name_element, "surname", surname)
        add_optional_element(builder, name_element, "given-names", given_names)
        if diagnostics is not None:
            diagnostics.info(
                _GENERATOR_NAME,
                f"BR-163: emitted structured name ({given_names} {surname}) for "
                f"reviewer {name!r} — matched an existing structured contrib "
                "record in the same source document.",
            )
    else:
        add_optional_element(builder, person, "string-name", name)
    add_optional_element(builder, person, "email", email)


def _format_answers(answers: tuple[tuple[str, str], ...]) -> str:
    return "; ".join(f"{key}: {value}" for key, value in answers)
