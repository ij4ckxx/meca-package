"""Unit tests for meca_engine.extraction.contributor_metadata_extractor."""

from __future__ import annotations

from pathlib import Path

import pytest

from meca_engine.extraction.contributor_metadata_extractor import extract_contributor_metadata
from meca_engine.extraction.parsed_model import (
    EncodingInfo,
    ParsedAttribute,
    ParsedDocument,
    ParsedElement,
)

pytestmark = pytest.mark.unit

_ENCODING = EncodingInfo(declared_encoding=None, bom_encoding=None, effective_encoding="utf-8")


def _document(root: ParsedElement) -> ParsedDocument:
    return ParsedDocument(source_path=Path("test.xml"), encoding=_ENCODING, doctype=None, root=root)


def _name(surname: str, given_names: str) -> ParsedElement:
    return ParsedElement(
        tag="name",
        namespace_uri=None,
        children=(
            ParsedElement(tag="surname", namespace_uri=None, text=surname),
            ParsedElement(tag="given-names", namespace_uri=None, text=given_names),
        ),
    )


def test_sorts_contributors_by_contrib_type() -> None:
    author = ParsedElement(
        tag="contrib",
        namespace_uri=None,
        attributes=(ParsedAttribute("contrib-type", None, "author"),),
        children=(_name("Doe", "Jane"),),
    )
    editor = ParsedElement(
        tag="contrib",
        namespace_uri=None,
        attributes=(ParsedAttribute("contrib-type", None, "editor"),),
        children=(_name("Smith", "John"),),
    )
    reviewer = ParsedElement(
        tag="contrib",
        namespace_uri=None,
        attributes=(ParsedAttribute("contrib-type", None, "reviewer"),),
        children=(_name("Lee", "Kim"),),
    )
    article_meta = ParsedElement(
        tag="article-meta", namespace_uri=None, children=(author, editor, reviewer)
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(article_meta,))

    metadata, diagnostics = extract_contributor_metadata(_document(root))

    assert len(metadata.authors) == 1
    assert metadata.authors[0].surname == "Doe"
    assert len(metadata.editors) == 1
    assert metadata.editors[0].surname == "Smith"
    assert len(metadata.other_contributors) == 1
    assert metadata.other_contributors[0].surname == "Lee"
    assert diagnostics == ()


def test_detects_corresponding_via_attribute() -> None:
    contrib = ParsedElement(
        tag="contrib",
        namespace_uri=None,
        attributes=(
            ParsedAttribute("contrib-type", None, "author"),
            ParsedAttribute("corresp", None, "yes"),
        ),
    )
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None, children=(contrib,))
    root = ParsedElement(tag="article", namespace_uri=None, children=(article_meta,))

    metadata, _ = extract_contributor_metadata(_document(root))

    assert metadata.authors[0].is_corresponding is True


def test_detects_corresponding_via_xref() -> None:
    xref = ParsedElement(
        tag="xref", namespace_uri=None, attributes=(ParsedAttribute("ref-type", None, "corresp"),)
    )
    contrib = ParsedElement(
        tag="contrib",
        namespace_uri=None,
        attributes=(ParsedAttribute("contrib-type", None, "author"),),
        children=(xref,),
    )
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None, children=(contrib,))
    root = ParsedElement(tag="article", namespace_uri=None, children=(article_meta,))

    metadata, _ = extract_contributor_metadata(_document(root))

    assert metadata.authors[0].is_corresponding is True


def test_extracts_orcid_emails_and_affiliation_refs() -> None:
    aff_xref = ParsedElement(
        tag="xref",
        namespace_uri=None,
        attributes=(ParsedAttribute("ref-type", None, "aff"), ParsedAttribute("rid", None, "aff1")),
    )
    contrib = ParsedElement(
        tag="contrib",
        namespace_uri=None,
        attributes=(ParsedAttribute("contrib-type", None, "author"),),
        children=(
            ParsedElement(tag="contrib-id", namespace_uri=None, text="0000-0001-2345-6789"),
            ParsedElement(tag="email", namespace_uri=None, text="jane@example.com"),
            aff_xref,
        ),
    )
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None, children=(contrib,))
    root = ParsedElement(tag="article", namespace_uri=None, children=(article_meta,))

    metadata, _ = extract_contributor_metadata(_document(root))

    author = metadata.authors[0]
    assert author.orcid == "0000-0001-2345-6789"
    assert author.emails == ("jane@example.com",)
    assert author.affiliation_ref_ids == ("aff1",)


def test_aff_xref_without_rid_contributes_no_ref_id() -> None:
    aff_xref = ParsedElement(
        tag="xref", namespace_uri=None, attributes=(ParsedAttribute("ref-type", None, "aff"),)
    )
    contrib = ParsedElement(
        tag="contrib",
        namespace_uri=None,
        attributes=(ParsedAttribute("contrib-type", None, "author"),),
        children=(aff_xref,),
    )
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None, children=(contrib,))
    root = ParsedElement(tag="article", namespace_uri=None, children=(article_meta,))

    metadata, _ = extract_contributor_metadata(_document(root))

    assert metadata.authors[0].affiliation_ref_ids == ()


def _named_content(content_type: str, text: str) -> ParsedElement:
    return ParsedElement(
        tag="named-content",
        namespace_uri=None,
        attributes=(ParsedAttribute("content-type", None, content_type),),
        text=text,
    )


def test_extracts_affiliations() -> None:
    aff = ParsedElement(
        tag="aff",
        namespace_uri=None,
        attributes=(ParsedAttribute("id", None, "aff1"),),
        children=(
            ParsedElement(tag="label", namespace_uri=None, text="1"),
            _named_content("dept", "Department of Chemistry"),
            _named_content("institution", "Example University"),
            _named_content("city", "Springfield"),
            _named_content("state", "IL"),
            _named_content("country", "USA"),
        ),
    )
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None, children=(aff,))
    root = ParsedElement(tag="article", namespace_uri=None, children=(article_meta,))

    metadata, _ = extract_contributor_metadata(_document(root))

    assert len(metadata.affiliations) == 1
    affiliation = metadata.affiliations[0]
    assert affiliation.element_id == "aff1"
    assert affiliation.label == "1"
    assert affiliation.department == "Department of Chemistry"
    assert affiliation.institution == "Example University"
    assert affiliation.city == "Springfield"
    assert affiliation.state == "IL"
    assert affiliation.country == "USA"


def test_affiliation_ignores_literal_jats_institution_and_country_tags() -> None:
    """Source never uses literal <institution>/<country>, only named-content — no false match."""
    aff = ParsedElement(
        tag="aff",
        namespace_uri=None,
        attributes=(ParsedAttribute("id", None, "aff1"),),
        children=(
            ParsedElement(tag="institution", namespace_uri=None, text="Should Not Match"),
            ParsedElement(tag="country", namespace_uri=None, text="Should Not Match"),
        ),
    )
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None, children=(aff,))
    root = ParsedElement(tag="article", namespace_uri=None, children=(article_meta,))

    metadata, _ = extract_contributor_metadata(_document(root))

    affiliation = metadata.affiliations[0]
    assert affiliation.institution is None
    assert affiliation.country is None
    assert "Should Not Match" in affiliation.raw_text


def test_extracts_suffix_and_equal_contrib() -> None:
    name = ParsedElement(
        tag="name",
        namespace_uri=None,
        children=(
            ParsedElement(tag="surname", namespace_uri=None, text="Doe"),
            ParsedElement(tag="given-names", namespace_uri=None, text="Jane"),
            ParsedElement(tag="suffix", namespace_uri=None, text="PhD"),
        ),
    )
    contrib = ParsedElement(
        tag="contrib",
        namespace_uri=None,
        attributes=(
            ParsedAttribute("contrib-type", None, "author"),
            ParsedAttribute("equal-contrib", None, "yes"),
        ),
        children=(name,),
    )
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None, children=(contrib,))
    root = ParsedElement(tag="article", namespace_uri=None, children=(article_meta,))

    metadata, _ = extract_contributor_metadata(_document(root))

    assert metadata.authors[0].suffix == "PhD"
    assert metadata.authors[0].equal_contrib is True


def test_missing_suffix_and_equal_contrib_default_to_falsy() -> None:
    contrib = ParsedElement(
        tag="contrib",
        namespace_uri=None,
        attributes=(ParsedAttribute("contrib-type", None, "author"),),
        children=(_name("Doe", "Jane"),),
    )
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None, children=(contrib,))
    root = ParsedElement(tag="article", namespace_uri=None, children=(article_meta,))

    metadata, _ = extract_contributor_metadata(_document(root))

    assert metadata.authors[0].suffix is None
    assert metadata.authors[0].equal_contrib is False


def test_missing_article_meta_returns_empty_metadata() -> None:
    root = ParsedElement(tag="article", namespace_uri=None)

    metadata, diagnostics = extract_contributor_metadata(_document(root))

    assert metadata.authors == ()
    assert metadata.affiliations == ()
    assert diagnostics == ()
