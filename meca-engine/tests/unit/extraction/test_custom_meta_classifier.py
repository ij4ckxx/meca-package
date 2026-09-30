"""Unit tests for meca_engine.extraction.custom_meta_classifier."""

from __future__ import annotations

import pytest

from meca_engine.extraction.custom_meta_classifier import classify
from meca_engine.extraction.metadata_models import (
    CustomMetadata,
    CustomMetaEntry,
    NamedContentField,
)
from meca_engine.model.enums import ReviewOutcomeStatus

pytestmark = pytest.mark.unit


def _file_entry(
    *,
    name: str = "figure",
    type_: str = "figure",
    path: str = "/ppl/cs/x/inputs/R1/fig1.jpg",
    size: str | None = None,
) -> CustomMetaEntry:
    named_content = [
        NamedContentField(content_type="type", text=type_),
        NamedContentField(content_type="name", text=name),
        NamedContentField(content_type="path", text=path),
    ]
    if size is not None:
        named_content.append(NamedContentField(content_type="size", text=size))
    return CustomMetaEntry(
        name=None,
        value_text="",
        named_content=tuple(named_content),
        attributes=(("specific-use", "form-files"),),
    )


def test_classifies_file_entry_from_specific_use() -> None:
    metadata = CustomMetadata(entries=(_file_entry(),))

    store = classify(metadata)

    assert len(store.file_entries) == 1
    entry = store.file_entries[0]
    assert entry.category == "figure"
    assert entry.original_filename == "figure"
    assert entry.round_label == "R1"
    assert entry.declared_path_hint == "/ppl/cs/x/inputs/R1/fig1.jpg"


def test_file_entry_parses_declared_size_when_present() -> None:
    metadata = CustomMetadata(entries=(_file_entry(size="102400"),))

    store = classify(metadata)

    assert store.file_entries[0].declared_size_bytes == 102400


def test_file_entry_without_size_leaves_it_none() -> None:
    metadata = CustomMetadata(entries=(_file_entry(),))

    store = classify(metadata)

    assert store.file_entries[0].declared_size_bytes is None


def test_multiple_file_entries_with_same_category_are_all_preserved() -> None:
    entries = (
        _file_entry(name="fig1", path="/ppl/cs/x/inputs/R1/fig1.jpg"),
        _file_entry(name="fig2", path="/ppl/cs/x/inputs/R1/fig2.jpg"),
    )
    metadata = CustomMetadata(entries=entries)

    store = classify(metadata)

    assert len(store.file_entries) == 2


def test_classifies_reviewer_scorecard_answers_grouped_by_reviewer_and_round() -> None:
    entry1 = CustomMetaEntry(
        name="QN_01",
        value_text="No",
        attributes=(
            ("specific-use", "question"),
            ("data-reviewer-name", "Jane Reviewer"),
            ("data-reviewer-email", "jane@example.com"),
            ("data-version", "Original"),
        ),
    )
    entry2 = CustomMetaEntry(
        name="QN_02",
        value_text="Yes",
        attributes=(
            ("specific-use", "question"),
            ("data-reviewer-name", "Jane Reviewer"),
            ("data-reviewer-email", "jane@example.com"),
            ("data-version", "Original"),
        ),
    )
    metadata = CustomMetadata(entries=(entry1, entry2))

    store = classify(metadata)

    assert len(store.reviewer_scorecards) == 1
    scorecard = store.reviewer_scorecards[0]
    assert scorecard.reviewer_name == "Jane Reviewer"
    assert scorecard.reviewer_email == "jane@example.com"
    assert scorecard.round_label == "Original"
    assert scorecard.answers == (("QN_01", "No"), ("QN_02", "Yes"))
    assert scorecard.outcome_status is ReviewOutcomeStatus.COMPLETED


def test_same_reviewer_different_rounds_produces_separate_scorecards() -> None:
    def _qn(round_label: str) -> CustomMetaEntry:
        return CustomMetaEntry(
            name="QN_01",
            value_text="No",
            attributes=(
                ("specific-use", "question"),
                ("data-reviewer-email", "jane@example.com"),
                ("data-version", round_label),
            ),
        )

    metadata = CustomMetadata(entries=(_qn("Original"), _qn("R1")))

    store = classify(metadata)

    assert len(store.reviewer_scorecards) == 2
    assert {s.round_label for s in store.reviewer_scorecards} == {"Original", "R1"}


def test_classifies_decision_draft_by_exact_name() -> None:
    entry = CustomMetaEntry(
        name="Decision Draft",
        value_text="Dear Author, ...",
        attributes=(("data-version", "R1"),),
    )
    metadata = CustomMetadata(entries=(entry,))

    store = classify(metadata)

    assert len(store.decision_drafts) == 1
    assert store.decision_drafts[0].round_label == "R1"
    assert store.decision_drafts[0].decision_text == "Dear Author, ..."


def test_classifies_decline_reason_from_specific_use() -> None:
    entry = CustomMetaEntry(
        name="reviewer-decline-reasons",
        value_text="",
        named_content=(NamedContentField(content_type="decline-reason", text="Too busy"),),
        attributes=(
            ("specific-use", "reviewer-decline"),
            ("data-reviewer-name", "David Kaye"),
            ("data-article-version", "Original"),
        ),
    )
    metadata = CustomMetadata(entries=(entry,))

    store = classify(metadata)

    assert len(store.decline_reasons) == 1
    reason = store.decline_reasons[0]
    assert reason.reviewer_name == "David Kaye"
    assert reason.round_label == "Original"
    assert reason.reason_text == "Too busy"


def test_track_changes_entries_are_excluded_from_form_answers() -> None:
    """Corrective-milestone fix: a "track-changes" entry has a real `meta-name`
    (unlike the "no meta-name" audit markers) but its value is always a
    synthetic "<field> was changed" audit message, never real form data.
    """
    entry = CustomMetaEntry(
        name="Figure 1",
        value_text="Figure 1 was changed",
        named_content=(NamedContentField(content_type="changeData", text="Figure 1 was changed"),),
        attributes=(
            ("specific-use", "track-changes"),
            ("data-username", "Kimberly Bayley (PUBLISHER)"),
        ),
    )
    metadata = CustomMetadata(entries=(entry,))

    store = classify(metadata)

    assert store.form_answers.entries == ()
    assert store.file_entries == ()
    assert store.reviewer_scorecards == ()
    assert store.decision_drafts == ()
    assert store.decline_reasons == ()


def test_track_changes_entries_are_excluded_alongside_legitimate_form_answers() -> None:
    entries = (
        CustomMetaEntry(
            name="PubData",
            value_text="PubData was changed",
            attributes=(("specific-use", "track-changes"),),
        ),
        CustomMetaEntry(name="Keyword", value_text="oncology"),
    )
    metadata = CustomMetadata(entries=entries)

    store = classify(metadata)

    assert store.form_answers.get("PubData") is None
    assert store.form_answers.get("Keyword") == ("oncology",)


def test_unclassified_named_entries_fall_through_to_form_answers() -> None:
    entry = CustomMetaEntry(name="Keyword", value_text="oncology")
    metadata = CustomMetadata(entries=(entry,))

    store = classify(metadata)

    assert store.form_answers.get("Keyword") == ("oncology",)


def test_repeated_key_form_answers_are_grouped_multi_valued() -> None:
    entries = (
        CustomMetaEntry(name="Authorship", value_text="Author 1 statement"),
        CustomMetaEntry(name="Authorship", value_text="Author 2 statement"),
    )
    metadata = CustomMetadata(entries=entries)

    store = classify(metadata)

    assert store.form_answers.get("Authorship") == (
        "Author 1 statement",
        "Author 2 statement",
    )


def test_entries_with_no_name_and_no_specific_classification_are_not_in_form_answers() -> None:
    entry = CustomMetaEntry(
        name=None,
        value_text="",
        attributes=(
            ("specific-use", "history"),
            ("data-user-role", "editor"),
            ("data-version", "Original"),
        ),
    )
    metadata = CustomMetadata(entries=(entry,))

    store = classify(metadata)

    assert store.form_answers.entries == ()
    assert store.file_entries == ()
    assert store.reviewer_scorecards == ()
    assert store.decision_drafts == ()
    assert store.decline_reasons == ()


def test_empty_custom_metadata_produces_empty_store() -> None:
    store = classify(CustomMetadata(entries=()))

    assert store.file_entries == ()
    assert store.reviewer_scorecards == ()
    assert store.decision_drafts == ()
    assert store.decline_reasons == ()
    assert store.form_answers.entries == ()
    assert store.workflow_log.events == ()


def test_logs_completion_with_per_collection_counts() -> None:
    import logging

    from meca_engine.logging_.structured_logger import StructuredLogger

    class _ListHandler(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.records: list[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    underlying = logging.getLogger("meca_engine.test.classify_logging")
    handler = _ListHandler()
    underlying.addHandler(handler)
    underlying.setLevel(logging.DEBUG)
    underlying.propagate = False

    logger = StructuredLogger("test.classify_logging")
    classify(CustomMetadata(entries=(_file_entry(),)), logger=logger)

    assert len(handler.records) == 1
    underlying.removeHandler(handler)
