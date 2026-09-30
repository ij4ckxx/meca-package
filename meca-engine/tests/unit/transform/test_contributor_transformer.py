"""Unit tests for meca_engine.transform.contributor_transformer."""

from __future__ import annotations

import pytest

from meca_engine.extraction.metadata_models import (
    AffiliationRecord,
    ContributorMetadata,
    ContributorRecord,
)
from meca_engine.model.article import (
    DeclineReason,
    FormAnswerBag,
    FormAnswerEntry,
    ReviewerScorecard,
)
from meca_engine.model.enums import ContribType, ReviewOutcomeStatus
from meca_engine.transform.contributor_transformer import build_contributors_and_affiliations

pytestmark = pytest.mark.unit


def _affiliation_record(
    *,
    element_id: str | None,
    institution: str | None,
    country: str | None,
    raw_text: str,
    label: str | None = None,
    department: str | None = None,
    city: str | None = None,
    state: str | None = None,
) -> AffiliationRecord:
    return AffiliationRecord(
        element_id=element_id,
        label=label,
        department=department,
        institution=institution,
        city=city,
        state=state,
        country=country,
        raw_text=raw_text,
    )


def test_assigns_sequential_model_internal_affiliation_keys() -> None:
    metadata = ContributorMetadata(
        affiliations=(
            _affiliation_record(element_id="aff1", institution="U1", country="USA", raw_text="U1"),
            _affiliation_record(element_id="aff2", institution="U2", country="UK", raw_text="U2"),
        )
    )

    _, affiliations, _ = build_contributors_and_affiliations(metadata)

    assert [a.model_key for a in affiliations] == [1, 2]


def test_maps_authors_and_editors_but_not_other_contributors() -> None:
    """Editors are mapped (Milestone 9); `other_contributors` remains genuinely out of scope."""
    metadata = ContributorMetadata(
        authors=(
            ContributorRecord(contrib_type="author", surname="Doe", given_names="Jane", orcid=None),
        ),
        editors=(
            ContributorRecord(contrib_type="editor", surname="Ed", given_names="Itor", orcid=None),
        ),
        other_contributors=(
            ContributorRecord(
                contrib_type="reviewer", surname="Rev", given_names="Iewer", orcid=None
            ),
        ),
    )

    contributors, _, _ = build_contributors_and_affiliations(metadata)

    assert [c.surname for c in contributors] == ["Doe", "Ed"]


def test_editor_maps_to_other_with_raw_contrib_type_preserved() -> None:
    metadata = ContributorMetadata(
        editors=(
            ContributorRecord(contrib_type="editor", surname="Ed", given_names="Itor", orcid=None),
        )
    )

    contributors, _, _ = build_contributors_and_affiliations(metadata)

    assert contributors[0].contrib_type is ContribType.OTHER
    assert contributors[0].raw_contrib_type == "editor"


def test_associate_editor_maps_to_its_own_contrib_type() -> None:
    metadata = ContributorMetadata(
        editors=(
            ContributorRecord(
                contrib_type="associate-editor", surname="Assoc", given_names="Editor", orcid=None
            ),
        )
    )

    contributors, _, _ = build_contributors_and_affiliations(metadata)

    assert contributors[0].contrib_type is ContribType.ASSOCIATE_EDITOR
    assert contributors[0].raw_contrib_type == "associate-editor"


def test_editors_repeated_across_snapshots_are_deduped_by_name() -> None:
    metadata = ContributorMetadata(
        editors=(
            ContributorRecord(
                contrib_type="editor", surname="Ed", given_names="Itor", orcid=None, emails=()
            ),
            ContributorRecord(
                contrib_type="editor",
                surname="ED",
                given_names="Itor",
                orcid=None,
                emails=("ed.itor@example.com",),
            ),
        )
    )

    contributors, _, _ = build_contributors_and_affiliations(metadata)

    assert len(contributors) == 1


def test_resolves_affiliation_ref_id_to_model_internal_key() -> None:
    metadata = ContributorMetadata(
        authors=(
            ContributorRecord(
                contrib_type="author",
                surname="Doe",
                given_names="Jane",
                orcid=None,
                affiliation_ref_ids=("aff2",),
            ),
        ),
        affiliations=(
            _affiliation_record(element_id="aff1", institution="U1", country=None, raw_text="U1"),
            _affiliation_record(element_id="aff2", institution="U2", country=None, raw_text="U2"),
        ),
    )

    contributors, _, _ = build_contributors_and_affiliations(metadata)

    assert contributors[0].affiliation_keys == (2,)


def test_dangling_affiliation_reference_without_logger_is_omitted_silently() -> None:
    metadata = ContributorMetadata(
        authors=(
            ContributorRecord(
                contrib_type="author",
                surname="Doe",
                given_names="Jane",
                orcid=None,
                affiliation_ref_ids=("missing-ref",),
            ),
        ),
    )

    contributors, _, _ = build_contributors_and_affiliations(metadata)

    assert contributors[0].affiliation_keys == ()


def test_affiliation_without_element_id_is_never_referenceable() -> None:
    metadata = ContributorMetadata(
        affiliations=(
            _affiliation_record(element_id=None, institution="U1", country=None, raw_text="U1"),
        )
    )

    _, affiliations, _ = build_contributors_and_affiliations(metadata)

    assert len(affiliations) == 1
    assert affiliations[0].model_key == 1


def test_dangling_affiliation_reference_is_omitted_and_logged() -> None:
    import logging

    from meca_engine.logging_.structured_logger import StructuredLogger

    class _ListHandler(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.records: list[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    underlying = logging.getLogger("meca_engine.test.dangling_affiliation")
    handler = _ListHandler()
    underlying.addHandler(handler)
    underlying.setLevel(logging.DEBUG)
    underlying.propagate = False

    metadata = ContributorMetadata(
        authors=(
            ContributorRecord(
                contrib_type="author",
                surname="Doe",
                given_names="Jane",
                orcid=None,
                affiliation_ref_ids=("missing-ref",),
            ),
        ),
    )

    contributors, _, _ = build_contributors_and_affiliations(
        metadata, logger=StructuredLogger("test.dangling_affiliation")
    )

    assert contributors[0].affiliation_keys == ()
    assert len(handler.records) == 1
    underlying.removeHandler(handler)


def test_institution_falls_back_to_raw_text_when_unstructured() -> None:
    metadata = ContributorMetadata(
        affiliations=(
            _affiliation_record(
                element_id="aff1", institution=None, country=None, raw_text="Dept X, City Y"
            ),
        )
    )

    _, affiliations, _ = build_contributors_and_affiliations(metadata)

    assert affiliations[0].institution == "Dept X, City Y"


def test_department_and_institution_are_joined_when_both_present() -> None:
    metadata = ContributorMetadata(
        affiliations=(
            _affiliation_record(
                element_id="aff1",
                institution="Example University",
                country=None,
                raw_text="ignored",
                label="1",
                department="Department of Chemistry",
                city="Springfield",
                state="IL",
            ),
        )
    )

    _, affiliations, _ = build_contributors_and_affiliations(metadata)

    affiliation = affiliations[0]
    assert affiliation.institution == "Department of Chemistry, Example University"
    assert affiliation.label == "1"
    assert affiliation.city == "Springfield"
    assert affiliation.state == "IL"


def test_corresponding_emails_collected_in_document_order() -> None:
    metadata = ContributorMetadata(
        authors=(
            ContributorRecord(
                contrib_type="author",
                surname="A",
                given_names="A",
                orcid=None,
                emails=("a@example.com",),
                is_corresponding=True,
            ),
            ContributorRecord(
                contrib_type="author",
                surname="B",
                given_names="B",
                orcid=None,
                emails=("b@example.com",),
                is_corresponding=False,
            ),
            ContributorRecord(
                contrib_type="author",
                surname="C",
                given_names="C",
                orcid=None,
                emails=("c@example.com",),
                is_corresponding=True,
            ),
        ),
    )

    _, _, corresponding_emails = build_contributors_and_affiliations(metadata)

    assert [e.email for e in corresponding_emails] == ["a@example.com", "c@example.com"]


def test_corresponding_author_without_email_contributes_no_corresp_email() -> None:
    metadata = ContributorMetadata(
        authors=(
            ContributorRecord(
                contrib_type="author",
                surname="A",
                given_names="A",
                orcid=None,
                is_corresponding=True,
            ),
        ),
    )

    _, _, corresponding_emails = build_contributors_and_affiliations(metadata)

    assert corresponding_emails == ()


def test_contributor_uses_first_email_when_multiple_present() -> None:
    metadata = ContributorMetadata(
        authors=(
            ContributorRecord(
                contrib_type="author",
                surname="A",
                given_names="A",
                orcid=None,
                emails=("first@example.com", "second@example.com"),
            ),
        ),
    )

    contributors, _, _ = build_contributors_and_affiliations(metadata)

    assert contributors[0].email == "first@example.com"


def test_reviewer_scorecard_becomes_reviewer_contributor() -> None:
    scorecards = (
        ReviewerScorecard(
            round_label="Original",
            reviewer_name="Jane Reviewer",
            reviewer_email="jane.reviewer@example.com",
            outcome_status=ReviewOutcomeStatus.COMPLETED,
        ),
    )

    contributors, _, _ = build_contributors_and_affiliations(
        ContributorMetadata(), reviewer_scorecards=scorecards
    )

    assert len(contributors) == 1
    reviewer = contributors[0]
    assert reviewer.contrib_type is ContribType.REVIEWER
    assert reviewer.full_name_raw == "Jane Reviewer"
    assert reviewer.email == "jane.reviewer@example.com"
    assert reviewer.raw_contrib_type == "reviewer"
    assert reviewer.surname == ""
    assert reviewer.given_names == ""


def test_reviewer_prefers_structured_contrib_data_when_matched_by_name() -> None:
    scorecards = (
        ReviewerScorecard(
            round_label="Original",
            reviewer_name="Jane Reviewer",
            reviewer_email="jane.reviewer@example.com",
            outcome_status=ReviewOutcomeStatus.COMPLETED,
        ),
    )
    structured = (
        ContributorRecord(
            contrib_type="reviewer",
            surname="Reviewer",
            given_names="Jane",
            orcid="0000-0000-0000-0001",
            emails=("jane.reviewer@example.com",),
        ),
    )

    contributors, _, _ = build_contributors_and_affiliations(
        ContributorMetadata(other_contributors=structured), reviewer_scorecards=scorecards
    )

    assert len(contributors) == 1
    reviewer = contributors[0]
    assert reviewer.surname == "Reviewer"
    assert reviewer.given_names == "Jane"
    assert reviewer.orcid == "0000-0000-0000-0001"
    assert reviewer.full_name_raw is None
    assert reviewer.contrib_type is ContribType.REVIEWER


def test_reviewer_falls_back_to_flattened_name_when_no_structured_match() -> None:
    scorecards = (
        ReviewerScorecard(
            round_label="Original",
            reviewer_name="Unmatched Reviewer",
            reviewer_email="unmatched@example.com",
            outcome_status=ReviewOutcomeStatus.COMPLETED,
        ),
    )
    structured = (
        ContributorRecord(
            contrib_type="reviewer", surname="Other", given_names="Person", orcid=None, emails=()
        ),
    )

    contributors, _, _ = build_contributors_and_affiliations(
        ContributorMetadata(other_contributors=structured), reviewer_scorecards=scorecards
    )

    assert len(contributors) == 1
    assert contributors[0].full_name_raw == "Unmatched Reviewer"
    assert contributors[0].surname == ""


def test_reviewer_structured_match_resolves_affiliation_xref() -> None:
    scorecards = (
        ReviewerScorecard(
            round_label="Original",
            reviewer_name="Jane Reviewer",
            reviewer_email=None,
            outcome_status=ReviewOutcomeStatus.COMPLETED,
        ),
    )
    structured = (
        ContributorRecord(
            contrib_type="reviewer",
            surname="Reviewer",
            given_names="Jane",
            orcid=None,
            emails=(),
            affiliation_ref_ids=("aff1",),
        ),
    )

    contributors, affiliations, _ = build_contributors_and_affiliations(
        ContributorMetadata(
            other_contributors=structured,
            affiliations=(
                _affiliation_record(element_id="aff1", institution="U1", country=None, raw_text=""),
            ),
        ),
        reviewer_scorecards=scorecards,
    )

    assert contributors[0].affiliation_keys == (affiliations[0].model_key,)


def test_same_reviewer_across_rounds_is_deduplicated() -> None:
    scorecards = (
        ReviewerScorecard(
            round_label="Original",
            reviewer_name="Jane Reviewer",
            reviewer_email="jane.reviewer@example.com",
            outcome_status=ReviewOutcomeStatus.COMPLETED,
        ),
        ReviewerScorecard(
            round_label="R1",
            reviewer_name="jane reviewer",
            reviewer_email="jane.reviewer@example.com",
            outcome_status=ReviewOutcomeStatus.COMPLETED,
        ),
    )

    contributors, _, _ = build_contributors_and_affiliations(
        ContributorMetadata(), reviewer_scorecards=scorecards
    )

    assert len(contributors) == 1


def test_blank_reviewer_name_is_skipped() -> None:
    scorecards = (
        ReviewerScorecard(
            round_label="Original",
            reviewer_name="   ",
            reviewer_email="",
            outcome_status=ReviewOutcomeStatus.COMPLETED,
        ),
    )

    contributors, _, _ = build_contributors_and_affiliations(
        ContributorMetadata(), reviewer_scorecards=scorecards
    )

    assert contributors == ()


def test_later_scorecard_backfills_missing_email_for_same_reviewer() -> None:
    scorecards = (
        ReviewerScorecard(
            round_label="Original",
            reviewer_name="Jane Reviewer",
            reviewer_email="",
            outcome_status=ReviewOutcomeStatus.COMPLETED,
        ),
        ReviewerScorecard(
            round_label="R1",
            reviewer_name="Jane Reviewer",
            reviewer_email="jane.reviewer@example.com",
            outcome_status=ReviewOutcomeStatus.COMPLETED,
        ),
    )

    contributors, _, _ = build_contributors_and_affiliations(
        ContributorMetadata(), reviewer_scorecards=scorecards
    )

    assert len(contributors) == 1
    assert contributors[0].email == "jane.reviewer@example.com"


def test_decline_reason_reviewer_has_no_email() -> None:
    decline_reasons = (
        DeclineReason(round_label="Original", reviewer_name="John Decliner", reason_text="Busy"),
    )

    contributors, _, _ = build_contributors_and_affiliations(
        ContributorMetadata(), decline_reasons=decline_reasons
    )

    assert len(contributors) == 1
    assert contributors[0].contrib_type is ContribType.REVIEWER
    assert contributors[0].full_name_raw == "John Decliner"
    assert contributors[0].email is None


def test_decline_reason_backfills_email_when_same_reviewer_also_scored() -> None:
    scorecards = (
        ReviewerScorecard(
            round_label="Original",
            reviewer_name="Jane Reviewer",
            reviewer_email="",
            outcome_status=ReviewOutcomeStatus.DECLINED,
        ),
    )
    decline_reasons = (
        DeclineReason(round_label="Original", reviewer_name="Jane Reviewer", reason_text="Busy"),
    )

    contributors, _, _ = build_contributors_and_affiliations(
        ContributorMetadata(), reviewer_scorecards=scorecards, decline_reasons=decline_reasons
    )

    assert len(contributors) == 1


def test_copyeditor_assigned_by_and_information_both_become_copy_editor_contributors() -> None:
    # Real source shape: `<meta-value><email>...</email><user-name>...</user-name></meta-value>`
    # flattens (Milestone 4) into one concatenated string with no separator.
    form_answers = FormAnswerBag(
        entries=(
            FormAnswerEntry(
                key="copyeditor assigned by",
                values=("gyanabati.l@kriyadocs.comGyanabati L",),
            ),
            FormAnswerEntry(
                key="copyeditor information",
                values=("shanthiselvamfreelance@gmail.comShanthipriya Selvam",),
            ),
        )
    )

    contributors, _, _ = build_contributors_and_affiliations(
        ContributorMetadata(), form_answers=form_answers
    )

    assert len(contributors) == 2
    assert all(c.contrib_type is ContribType.COPY_EDITOR for c in contributors)
    assert contributors[0].full_name_raw == "Gyanabati L"
    assert contributors[0].email == "gyanabati.l@kriyadocs.com"
    assert contributors[0].raw_contrib_type == "copyeditor assigned by"
    assert contributors[1].full_name_raw == "Shanthipriya Selvam"
    assert contributors[1].email == "shanthiselvamfreelance@gmail.com"
    assert contributors[1].raw_contrib_type == "copyeditor information"


def test_copyeditor_value_with_no_email_becomes_name_only_contributor() -> None:
    form_answers = FormAnswerBag(
        entries=(FormAnswerEntry(key="copyeditor information", values=("Kavitha D",)),)
    )

    contributors, _, _ = build_contributors_and_affiliations(
        ContributorMetadata(), form_answers=form_answers
    )

    assert len(contributors) == 1
    assert contributors[0].full_name_raw == "Kavitha D"
    assert contributors[0].email is None


def test_blank_copyeditor_value_produces_no_contributor() -> None:
    form_answers = FormAnswerBag(
        entries=(FormAnswerEntry(key="copyeditor information", values=("   ",)),)
    )

    contributors, _, _ = build_contributors_and_affiliations(
        ContributorMetadata(), form_answers=form_answers
    )

    assert contributors == ()


def test_missing_copyeditor_form_answers_produce_no_copy_editor_contributors() -> None:
    contributors, _, _ = build_contributors_and_affiliations(
        ContributorMetadata(), form_answers=FormAnswerBag()
    )

    assert contributors == ()


def test_contributors_ordered_authors_then_reviewers_then_copy_editors() -> None:
    metadata = ContributorMetadata(
        authors=(
            ContributorRecord(contrib_type="author", surname="Doe", given_names="Jane", orcid=None),
        ),
    )
    scorecards = (
        ReviewerScorecard(
            round_label="Original",
            reviewer_name="Jane Reviewer",
            reviewer_email="jane.reviewer@example.com",
            outcome_status=ReviewOutcomeStatus.COMPLETED,
        ),
    )
    form_answers = FormAnswerBag(
        entries=(FormAnswerEntry(key="copyeditor information", values=("Kavitha D",)),)
    )

    contributors, _, _ = build_contributors_and_affiliations(
        metadata, reviewer_scorecards=scorecards, form_answers=form_answers
    )

    assert [c.contrib_type for c in contributors] == [
        ContribType.AUTHOR,
        ContribType.REVIEWER,
        ContribType.COPY_EDITOR,
    ]


def test_empty_metadata_produces_empty_results() -> None:
    contributors, affiliations, corresponding_emails = build_contributors_and_affiliations(
        ContributorMetadata()
    )

    assert contributors == ()
    assert affiliations == ()
    assert corresponding_emails == ()
