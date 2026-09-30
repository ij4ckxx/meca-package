"""Unit tests for meca_engine.transform.journal_transformer."""

from __future__ import annotations

import pytest

from meca_engine.extraction.metadata_models import JournalMetadata
from meca_engine.transform.journal_transformer import build_journal_meta

pytestmark = pytest.mark.unit


def test_maps_fields_verbatim() -> None:
    metadata = JournalMetadata(
        journal_title="Journal of Examples",
        publisher_name="Example Press",
        issns=(("ppub", "1234-5678"), ("epub", "8765-4321")),
        abbrev_titles=(("pubmed", "J. Ex."),),
    )

    journal_meta = build_journal_meta(metadata)

    assert journal_meta.journal_title == "Journal of Examples"
    assert journal_meta.publisher_name == "Example Press"
    assert journal_meta.issn_ppub == "1234-5678"
    assert journal_meta.issn_epub == "8765-4321"
    assert journal_meta.abbrev_titles == (("pubmed", "J. Ex."),)


def test_missing_issn_type_leaves_field_none() -> None:
    metadata = JournalMetadata(issns=(("ppub", "1234-5678"),))

    journal_meta = build_journal_meta(metadata)

    assert journal_meta.issn_ppub == "1234-5678"
    assert journal_meta.issn_epub is None


def test_missing_title_and_publisher_become_empty_strings() -> None:
    journal_meta = build_journal_meta(JournalMetadata())

    assert journal_meta.journal_title == ""
    assert journal_meta.publisher_name == ""


def test_abbrev_titles_with_none_type_are_filtered() -> None:
    metadata = JournalMetadata(abbrev_titles=((None, "Some Title"), ("pubmed", "J. Ex.")))

    journal_meta = build_journal_meta(metadata)

    assert journal_meta.abbrev_titles == (("pubmed", "J. Ex."),)


def test_maps_journal_ids_and_placement_fields() -> None:
    metadata = JournalMetadata(
        journal_ids=(("publisher-id", "bcj"), ("nlm-ta", "bcj")),
        volume="12",
        issue="3",
        fpage="100",
        lpage="120",
    )

    journal_meta = build_journal_meta(metadata)

    assert journal_meta.journal_ids == (("publisher-id", "bcj"), ("nlm-ta", "bcj"))
    assert journal_meta.volume == "12"
    assert journal_meta.issue == "3"
    assert journal_meta.fpage == "100"
    assert journal_meta.lpage == "120"


def test_journal_ids_with_none_type_are_filtered() -> None:
    metadata = JournalMetadata(journal_ids=((None, "Some Id"), ("publisher-id", "bcj")))

    journal_meta = build_journal_meta(metadata)

    assert journal_meta.journal_ids == (("publisher-id", "bcj"),)
