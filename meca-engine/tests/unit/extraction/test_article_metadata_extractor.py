"""Unit tests for meca_engine.extraction.article_metadata_extractor."""

from __future__ import annotations

from pathlib import Path

import pytest

from meca_engine.extraction.article_metadata_extractor import extract_article_metadata
from meca_engine.extraction.metadata_models import ArticleIdentifier
from meca_engine.extraction.navigation import XML_NAMESPACE_URI
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


def test_extracts_identifiers_title_and_type() -> None:
    article_id = ParsedElement(
        tag="article-id",
        namespace_uri=None,
        attributes=(ParsedAttribute("pub-id-type", None, "doi"),),
        text="10.1234/x",
    )
    title = ParsedElement(tag="article-title", namespace_uri=None, text="A Title")
    title_group = ParsedElement(tag="title-group", namespace_uri=None, children=(title,))
    article_meta = ParsedElement(
        tag="article-meta", namespace_uri=None, children=(article_id, title_group)
    )
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        attributes=(ParsedAttribute("article-type", None, "research-article"),),
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    metadata, diagnostics = extract_article_metadata(_document(root))

    assert metadata.identifiers == (ArticleIdentifier(id_type="doi", value="10.1234/x"),)
    assert metadata.title == "A Title"
    assert metadata.article_type == "research-article"
    assert diagnostics == ()


def test_missing_article_meta_produces_diagnostic() -> None:
    root = ParsedElement(tag="article", namespace_uri=None)

    metadata, diagnostics = extract_article_metadata(_document(root))

    assert metadata.identifiers == ()
    assert len(diagnostics) == 1
    assert diagnostics[0].category is DiagnosticCategory.MISSING_REQUIRED_VALUE


def test_missing_identifiers_and_title_each_produce_a_diagnostic() -> None:
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None)
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    metadata, diagnostics = extract_article_metadata(_document(root))

    assert metadata.title is None
    assert len(diagnostics) == 2
    assert all(d.category is DiagnosticCategory.MISSING_REQUIRED_VALUE for d in diagnostics)


def test_extracts_history_and_pub_dates() -> None:
    received = ParsedElement(
        tag="date",
        namespace_uri=None,
        attributes=(ParsedAttribute("date-type", None, "received"),),
        children=(
            ParsedElement(tag="year", namespace_uri=None, text="2025"),
            ParsedElement(tag="month", namespace_uri=None, text="01"),
            ParsedElement(tag="day", namespace_uri=None, text="15"),
        ),
    )
    history = ParsedElement(tag="history", namespace_uri=None, children=(received,))
    pub_date = ParsedElement(
        tag="pub-date",
        namespace_uri=None,
        attributes=(ParsedAttribute("date-type", None, "pub"),),
        children=(ParsedElement(tag="year", namespace_uri=None, text="2025"),),
    )
    article_meta = ParsedElement(
        tag="article-meta", namespace_uri=None, children=(history, pub_date)
    )
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    metadata, _ = extract_article_metadata(_document(root))

    assert len(metadata.history_dates) == 1
    assert metadata.history_dates[0].date_type == "received"
    assert metadata.history_dates[0].year == "2025"
    assert metadata.history_dates[0].month == "01"
    assert metadata.history_dates[0].day == "15"
    assert len(metadata.pub_dates) == 1
    assert metadata.pub_dates[0].date_type == "pub"


def test_pub_date_falls_back_to_pub_type_attribute() -> None:
    """Real source tags <pub-date> with pub-type, never date-type."""
    epub = ParsedElement(
        tag="pub-date",
        namespace_uri=None,
        attributes=(ParsedAttribute("pub-type", None, "epub"),),
        children=(ParsedElement(tag="year", namespace_uri=None, text="2025"),),
    )
    ppub = ParsedElement(
        tag="pub-date",
        namespace_uri=None,
        attributes=(ParsedAttribute("pub-type", None, "ppub"),),
        children=(ParsedElement(tag="year", namespace_uri=None, text="2025"),),
    )
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None, children=(epub, ppub))
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    metadata, _ = extract_article_metadata(_document(root))

    assert [record.date_type for record in metadata.pub_dates] == ["epub", "ppub"]


def test_extracts_display_channel_and_heading_subjects() -> None:
    display_channel = ParsedElement(
        tag="subj-group",
        namespace_uri=None,
        attributes=(ParsedAttribute("subj-group-type", None, "display-channel"),),
        children=(ParsedElement(tag="subject", namespace_uri=None, text="Research Article"),),
    )
    heading_one = ParsedElement(
        tag="subj-group",
        namespace_uri=None,
        attributes=(ParsedAttribute("subj-group-type", None, "heading"),),
        children=(ParsedElement(tag="subject", namespace_uri=None, text="Cell Biology"),),
    )
    heading_two = ParsedElement(
        tag="subj-group",
        namespace_uri=None,
        attributes=(ParsedAttribute("subj-group-type", None, "heading"),),
        children=(ParsedElement(tag="subject", namespace_uri=None, text="Signaling"),),
    )
    categories = ParsedElement(
        tag="article-categories",
        namespace_uri=None,
        children=(display_channel, heading_one, heading_two),
    )
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None, children=(categories,))
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    metadata, _ = extract_article_metadata(_document(root))

    assert metadata.display_channel_subject == "Research Article"
    assert metadata.heading_subjects == ("Cell Biology", "Signaling")


def test_subj_group_without_subject_child_is_skipped() -> None:
    empty_subj_group = ParsedElement(
        tag="subj-group",
        namespace_uri=None,
        attributes=(ParsedAttribute("subj-group-type", None, "heading"),),
    )
    categories = ParsedElement(
        tag="article-categories", namespace_uri=None, children=(empty_subj_group,)
    )
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None, children=(categories,))
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    metadata, _ = extract_article_metadata(_document(root))

    assert metadata.heading_subjects == ()


def test_missing_subj_group_leaves_display_channel_none_and_headings_empty() -> None:
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None)
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    metadata, _ = extract_article_metadata(_document(root))

    assert metadata.display_channel_subject is None
    assert metadata.heading_subjects == ()


def test_extracts_copyright_keywords_funding_and_counts() -> None:
    permissions = ParsedElement(
        tag="permissions",
        namespace_uri=None,
        children=(
            ParsedElement(tag="copyright-statement", namespace_uri=None, text="(c) 2025"),
            ParsedElement(tag="copyright-year", namespace_uri=None, text="2025"),
        ),
    )
    kwd_group = ParsedElement(
        tag="kwd-group",
        namespace_uri=None,
        children=(
            ParsedElement(tag="kwd", namespace_uri=None, text="oncology"),
            ParsedElement(tag="kwd", namespace_uri=None, text="genomics"),
        ),
    )
    funding_group = ParsedElement(
        tag="funding-group", namespace_uri=None, text="Example Foundation Grant 123"
    )
    counts = ParsedElement(
        tag="counts",
        namespace_uri=None,
        children=(
            ParsedElement(
                tag="word-count",
                namespace_uri=None,
                attributes=(ParsedAttribute("count", None, "5000"),),
            ),
            ParsedElement(
                tag="ref-count",
                namespace_uri=None,
                attributes=(ParsedAttribute("count", None, "42"),),
            ),
            ParsedElement(
                tag="fig-count",
                namespace_uri=None,
                attributes=(ParsedAttribute("count", None, "3"),),
            ),
            ParsedElement(
                tag="table-count",
                namespace_uri=None,
                attributes=(ParsedAttribute("count", None, "2"),),
            ),
            ParsedElement(
                tag="equation-count",
                namespace_uri=None,
                attributes=(ParsedAttribute("count", None, "1"),),
            ),
            ParsedElement(
                tag="page-count",
                namespace_uri=None,
                attributes=(ParsedAttribute("count", None, "10"),),
            ),
        ),
    )
    article_meta = ParsedElement(
        tag="article-meta",
        namespace_uri=None,
        children=(permissions, kwd_group, funding_group, counts),
    )
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    metadata, _ = extract_article_metadata(_document(root))

    assert metadata.copyright_statement == "(c) 2025"
    assert metadata.copyright_year == "2025"
    assert metadata.keywords == ("oncology", "genomics")
    assert metadata.funding_statements == ("Example Foundation Grant 123",)
    assert metadata.word_count == "5000"
    assert metadata.ref_count == "42"
    assert metadata.fig_count == "3"
    assert metadata.table_count == "2"
    assert metadata.equation_count == "1"
    assert metadata.page_count == "10"


def test_missing_permissions_kwd_funding_counts_leave_fields_empty() -> None:
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None)
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    metadata, _ = extract_article_metadata(_document(root))

    assert metadata.copyright_statement is None
    assert metadata.copyright_year is None
    assert metadata.keywords == ()
    assert metadata.funding_statements == ()
    assert metadata.word_count is None
    assert metadata.ref_count is None
    assert metadata.fig_count is None
    assert metadata.table_count is None
    assert metadata.equation_count is None
    assert metadata.page_count is None


def test_extracts_single_abstract_text() -> None:
    paragraph = ParsedElement(tag="p", namespace_uri=None, text="This study examines X.")
    abstract = ParsedElement(tag="abstract", namespace_uri=None, children=(paragraph,))
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None, children=(abstract,))
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    metadata, _ = extract_article_metadata(_document(root))

    assert len(metadata.abstracts) == 1
    assert metadata.abstracts[0].text == "This study examines X."
    assert metadata.abstracts[0].abstract_type is None
    assert metadata.abstracts[0].language is None


def test_extracts_abstract_type_and_namespaced_language() -> None:
    abstract = ParsedElement(
        tag="abstract",
        namespace_uri=None,
        attributes=(
            ParsedAttribute("abstract-type", None, "graphical"),
            ParsedAttribute("lang", XML_NAMESPACE_URI, "en"),
        ),
        children=(ParsedElement(tag="p", namespace_uri=None, text="Summary."),),
    )
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None, children=(abstract,))
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    metadata, _ = extract_article_metadata(_document(root))

    assert metadata.abstracts[0].abstract_type == "graphical"
    assert metadata.abstracts[0].language == "en"


def test_extracts_multiple_abstracts_in_document_order() -> None:
    main_abstract = ParsedElement(tag="abstract", namespace_uri=None, text="Main abstract text.")
    plain_language_abstract = ParsedElement(
        tag="abstract",
        namespace_uri=None,
        attributes=(ParsedAttribute("abstract-type", None, "plain-language-summary"),),
        text="Plain language summary text.",
    )
    article_meta = ParsedElement(
        tag="article-meta",
        namespace_uri=None,
        children=(main_abstract, plain_language_abstract),
    )
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    metadata, _ = extract_article_metadata(_document(root))

    assert len(metadata.abstracts) == 2
    assert metadata.abstracts[0].text == "Main abstract text."
    assert metadata.abstracts[0].abstract_type is None
    assert metadata.abstracts[1].text == "Plain language summary text."
    assert metadata.abstracts[1].abstract_type == "plain-language-summary"


def test_missing_abstract_leaves_abstracts_empty() -> None:
    article_meta = ParsedElement(tag="article-meta", namespace_uri=None)
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    metadata, _ = extract_article_metadata(_document(root))

    assert metadata.abstracts == ()


def test_publication_status_and_language_preserved_verbatim() -> None:
    article_meta = ParsedElement(
        tag="article-meta",
        namespace_uri=None,
        attributes=(ParsedAttribute("publication-status", None, "in-press"),),
    )
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        attributes=(ParsedAttribute("lang", None, "en"),),
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    metadata, _ = extract_article_metadata(_document(root))

    assert metadata.publication_status == "in-press"
    assert metadata.language == "en"
