"""Unit tests for meca_engine.extraction.journal_metadata_extractor."""

from __future__ import annotations

from pathlib import Path

import pytest

from meca_engine.extraction.journal_metadata_extractor import extract_journal_metadata
from meca_engine.extraction.parsed_model import (
    DiagnosticCategory,
    EncodingInfo,
    ParsedAttribute,
    ParsedDocument,
    ParsedElement,
)

pytestmark = pytest.mark.unit

_ENCODING = EncodingInfo(declared_encoding=None, bom_encoding=None, effective_encoding="utf-8")


def _document(root: ParsedElement) -> ParsedDocument:
    return ParsedDocument(source_path=Path("test.xml"), encoding=_ENCODING, doctype=None, root=root)


def test_extracts_journal_title_issns_and_publisher() -> None:
    journal_meta = ParsedElement(
        tag="journal-meta",
        namespace_uri=None,
        children=(
            ParsedElement(tag="journal-title", namespace_uri=None, text="Journal of Examples"),
            ParsedElement(
                tag="issn",
                namespace_uri=None,
                attributes=(ParsedAttribute("pub-type", None, "epub"),),
                text="1234-5678",
            ),
            ParsedElement(tag="publisher-name", namespace_uri=None, text="Example Press"),
        ),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(journal_meta,))

    metadata, diagnostics = extract_journal_metadata(_document(root))

    assert metadata.journal_title == "Journal of Examples"
    assert metadata.issns == (("epub", "1234-5678"),)
    assert metadata.publisher_name == "Example Press"
    assert diagnostics == ()


def test_extracts_journal_id_from_publisher_id_typed_journal_id() -> None:
    journal_meta = ParsedElement(
        tag="journal-meta",
        namespace_uri=None,
        children=(
            ParsedElement(
                tag="journal-id",
                namespace_uri=None,
                attributes=(ParsedAttribute("journal-id-type", None, "nlm-ta"),),
                text="cs",
            ),
            ParsedElement(
                tag="journal-id",
                namespace_uri=None,
                attributes=(ParsedAttribute("journal-id-type", None, "publisher-id"),),
                text="CS",
            ),
        ),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(journal_meta,))

    metadata, _ = extract_journal_metadata(_document(root))

    assert metadata.journal_id == "CS"
    assert metadata.journal_ids == (("nlm-ta", "cs"), ("publisher-id", "CS"))


def test_extracts_abbrev_journal_titles() -> None:
    journal_meta = ParsedElement(
        tag="journal-meta",
        namespace_uri=None,
        children=(
            ParsedElement(
                tag="abbrev-journal-title",
                namespace_uri=None,
                attributes=(ParsedAttribute("abbrev-type", None, "pubmed"),),
                text="Clin. Sci.",
            ),
        ),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(journal_meta,))

    metadata, _ = extract_journal_metadata(_document(root))

    assert metadata.abbrev_titles == (("pubmed", "Clin. Sci."),)


def test_missing_journal_id_leaves_field_none() -> None:
    journal_meta = ParsedElement(
        tag="journal-meta",
        namespace_uri=None,
        children=(ParsedElement(tag="journal-title", namespace_uri=None, text="X"),),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(journal_meta,))

    metadata, _ = extract_journal_metadata(_document(root))

    assert metadata.journal_id is None


def test_missing_journal_title_produces_diagnostic() -> None:
    journal_meta = ParsedElement(tag="journal-meta", namespace_uri=None)
    root = ParsedElement(tag="article", namespace_uri=None, children=(journal_meta,))

    metadata, diagnostics = extract_journal_metadata(_document(root))

    assert metadata.journal_title is None
    assert len(diagnostics) == 1
    assert diagnostics[0].category is DiagnosticCategory.MISSING_REQUIRED_VALUE


def test_extracts_volume_issue_and_pages_from_article_meta() -> None:
    article_meta = ParsedElement(
        tag="article-meta",
        namespace_uri=None,
        children=(
            ParsedElement(tag="volume", namespace_uri=None, text="12"),
            ParsedElement(tag="issue", namespace_uri=None, text="3"),
            ParsedElement(tag="fpage", namespace_uri=None, text="100"),
            ParsedElement(tag="lpage", namespace_uri=None, text="110"),
            ParsedElement(tag="elocation-id", namespace_uri=None, text="e12345"),
        ),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(article_meta,))

    metadata, _ = extract_journal_metadata(_document(root))

    assert metadata.volume == "12"
    assert metadata.issue == "3"
    assert metadata.fpage == "100"
    assert metadata.lpage == "110"
    assert metadata.elocation_id == "e12345"


def test_doi_related_ids_reuses_article_metadata_identifiers() -> None:
    doi_id = ParsedElement(
        tag="article-id",
        namespace_uri=None,
        attributes=(ParsedAttribute("pub-id-type", None, "doi"),),
        text="10.1234/y",
    )
    other_id = ParsedElement(
        tag="article-id",
        namespace_uri=None,
        attributes=(ParsedAttribute("pub-id-type", None, "publisher-id"),),
        text="PUB-1",
    )
    article_meta = ParsedElement(
        tag="article-meta", namespace_uri=None, children=(doi_id, other_id)
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(article_meta,))

    metadata, _ = extract_journal_metadata(_document(root))

    assert metadata.doi_related_ids == ("10.1234/y",)


def test_missing_journal_meta_and_article_meta_returns_empty_metadata() -> None:
    root = ParsedElement(tag="article", namespace_uri=None)

    metadata, diagnostics = extract_journal_metadata(_document(root))

    assert metadata.journal_title is None
    assert metadata.volume is None
    assert len(diagnostics) == 1
