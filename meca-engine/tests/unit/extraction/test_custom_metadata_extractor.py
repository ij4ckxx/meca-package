"""Unit tests for meca_engine.extraction.custom_metadata_extractor."""

from __future__ import annotations

from pathlib import Path

import pytest

from meca_engine.extraction.custom_metadata_extractor import extract_custom_metadata
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


def test_extracts_name_and_value() -> None:
    entry = ParsedElement(
        tag="custom-meta",
        namespace_uri=None,
        children=(
            ParsedElement(tag="meta-name", namespace_uri=None, text="review-type"),
            ParsedElement(tag="meta-value", namespace_uri=None, text="single-blind"),
        ),
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(entry,))

    metadata, diagnostics = extract_custom_metadata(_document(root))

    assert len(metadata.entries) == 1
    assert metadata.entries[0].name == "review-type"
    assert metadata.entries[0].value_text == "single-blind"
    assert diagnostics == ()


def test_extracts_named_content_within_value() -> None:
    named_content = ParsedElement(
        tag="named-content",
        namespace_uri=None,
        attributes=(ParsedAttribute("content-type", None, "flag"),),
        text="yes",
    )
    value = ParsedElement(tag="meta-value", namespace_uri=None, children=(named_content,))
    entry = ParsedElement(
        tag="custom-meta",
        namespace_uri=None,
        children=(ParsedElement(tag="meta-name", namespace_uri=None, text="x"), value),
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(entry,))

    metadata, _ = extract_custom_metadata(_document(root))

    assert len(metadata.entries[0].named_content) == 1
    assert metadata.entries[0].named_content[0].content_type == "flag"
    assert metadata.entries[0].named_content[0].text == "yes"


def test_extracts_named_content_using_data_type_when_content_type_absent() -> None:
    """Milestone 9 correction: real production packages have been observed
    spelling this attribute ``data-type`` instead of ``content-type``."""
    named_content = ParsedElement(
        tag="named-content",
        namespace_uri=None,
        attributes=(ParsedAttribute("data-type", None, "name"),),
        text="Fig1",
    )
    value = ParsedElement(tag="meta-value", namespace_uri=None, children=(named_content,))
    entry = ParsedElement(
        tag="custom-meta",
        namespace_uri=None,
        children=(ParsedElement(tag="meta-name", namespace_uri=None, text="figure"), value),
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(entry,))

    metadata, _ = extract_custom_metadata(_document(root))

    assert metadata.entries[0].named_content[0].content_type == "name"
    assert metadata.entries[0].named_content[0].text == "Fig1"


def test_content_type_takes_priority_over_data_type_when_both_present() -> None:
    """Backwards compatibility: a previously-processed package's exact
    behavior must not change if it happens to carry both attributes."""
    named_content = ParsedElement(
        tag="named-content",
        namespace_uri=None,
        attributes=(
            ParsedAttribute("content-type", None, "licenseType"),
            ParsedAttribute("data-type", None, "some-other-value"),
        ),
        text="CC BY",
    )
    value = ParsedElement(tag="meta-value", namespace_uri=None, children=(named_content,))
    entry = ParsedElement(
        tag="custom-meta",
        namespace_uri=None,
        children=(ParsedElement(tag="meta-name", namespace_uri=None, text="License Type"), value),
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(entry,))

    metadata, _ = extract_custom_metadata(_document(root))

    assert metadata.entries[0].named_content[0].content_type == "licenseType"


def test_named_content_with_neither_attribute_is_none() -> None:
    named_content = ParsedElement(
        tag="named-content", namespace_uri=None, attributes=(), text="untyped"
    )
    value = ParsedElement(tag="meta-value", namespace_uri=None, children=(named_content,))
    entry = ParsedElement(
        tag="custom-meta",
        namespace_uri=None,
        children=(ParsedElement(tag="meta-name", namespace_uri=None, text="x"), value),
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(entry,))

    metadata, _ = extract_custom_metadata(_document(root))

    assert metadata.entries[0].named_content[0].content_type is None


def test_includes_every_entry_unfiltered() -> None:
    entries = tuple(
        ParsedElement(
            tag="custom-meta",
            namespace_uri=None,
            children=(ParsedElement(tag="meta-name", namespace_uri=None, text=f"key-{i}"),),
        )
        for i in range(3)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=entries)

    metadata, _ = extract_custom_metadata(_document(root))

    assert len(metadata.entries) == 3


def test_no_entries_produces_empty_metadata() -> None:
    root = ParsedElement(tag="root", namespace_uri=None)

    metadata, diagnostics = extract_custom_metadata(_document(root))

    assert metadata.entries == ()
    assert diagnostics == ()


def test_extracts_custom_meta_element_attributes() -> None:
    entry = ParsedElement(
        tag="custom-meta",
        namespace_uri=None,
        attributes=(
            ParsedAttribute("specific-use", None, "question"),
            ParsedAttribute("data-version", None, "Original"),
        ),
        children=(ParsedElement(tag="meta-name", namespace_uri=None, text="QN_01"),),
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(entry,))

    metadata, _ = extract_custom_metadata(_document(root))

    assert metadata.entries[0].attributes == (
        ("specific-use", "question"),
        ("data-version", "Original"),
    )


def test_ignores_namespaced_custom_meta_attributes() -> None:
    entry = ParsedElement(
        tag="custom-meta",
        namespace_uri=None,
        attributes=(ParsedAttribute("lang", "urn:other", "en"),),
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(entry,))

    metadata, _ = extract_custom_metadata(_document(root))

    assert metadata.entries[0].attributes == ()


def test_missing_meta_name_leaves_name_none() -> None:
    entry = ParsedElement(
        tag="custom-meta",
        namespace_uri=None,
        children=(ParsedElement(tag="meta-value", namespace_uri=None, text="value only"),),
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(entry,))

    metadata, _ = extract_custom_metadata(_document(root))

    assert metadata.entries[0].name is None
    assert metadata.entries[0].value_text == "value only"
