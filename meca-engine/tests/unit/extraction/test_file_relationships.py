"""Unit tests for meca_engine.extraction.file_relationships."""

from __future__ import annotations

from pathlib import Path

import pytest

from meca_engine.extraction.file_relationships import (
    XLINK_NAMESPACE_URI,
    discover_file_references,
)
from meca_engine.extraction.parsed_model import (
    EncodingInfo,
    ParsedAttribute,
    ParsedDocument,
    ParsedElement,
)

pytestmark = pytest.mark.unit


def _document(root: ParsedElement) -> ParsedDocument:
    return ParsedDocument(
        source_path=Path("/tmp/x.xml"),
        encoding=EncodingInfo(
            declared_encoding=None, bom_encoding=None, effective_encoding="utf-8"
        ),
        doctype=None,
        root=root,
    )


def test_discovers_xlink_href_reference() -> None:
    graphic = ParsedElement(
        tag="graphic",
        namespace_uri=None,
        attributes=(
            ParsedAttribute(name="href", namespace_uri=XLINK_NAMESPACE_URI, value="fig1.jpg"),
        ),
    )
    root = ParsedElement(tag="body", namespace_uri=None, children=(graphic,))

    refs = discover_file_references(_document(root))

    assert len(refs) == 1
    assert refs[0].referencing_tag == "graphic"
    assert refs[0].attribute_name == "href"
    assert refs[0].attribute_namespace_uri == XLINK_NAMESPACE_URI
    assert refs[0].value == "fig1.jpg"


def test_discovers_plain_href_and_src() -> None:
    ext_link = ParsedElement(
        tag="ext-link",
        namespace_uri=None,
        attributes=(
            ParsedAttribute(name="href", namespace_uri=None, value="https://example.org/related"),
        ),
    )
    media = ParsedElement(
        tag="media",
        namespace_uri=None,
        attributes=(ParsedAttribute(name="src", namespace_uri=None, value="video.mp4"),),
    )
    root = ParsedElement(tag="body", namespace_uri=None, children=(ext_link, media))

    refs = discover_file_references(_document(root))

    values = {r.value for r in refs}
    assert values == {"https://example.org/related", "video.mp4"}


def test_discovers_multiple_reference_shapes_together() -> None:
    # Mirrors the realistic variety the task names: images, supplementary
    # material, and related resources — all found via the same generic
    # mechanism, with no tag-specific business logic.
    graphic = ParsedElement(
        tag="graphic",
        namespace_uri=None,
        attributes=(
            ParsedAttribute(name="href", namespace_uri=XLINK_NAMESPACE_URI, value="fig1.jpg"),
        ),
    )
    supplement = ParsedElement(
        tag="supplementary-material",
        namespace_uri=None,
        attributes=(
            ParsedAttribute(name="href", namespace_uri=XLINK_NAMESPACE_URI, value="supp1.pdf"),
        ),
    )
    ext_link = ParsedElement(
        tag="ext-link",
        namespace_uri=None,
        attributes=(
            ParsedAttribute(
                name="href", namespace_uri=XLINK_NAMESPACE_URI, value="https://example.org"
            ),
        ),
    )
    root = ParsedElement(tag="body", namespace_uri=None, children=(graphic, supplement, ext_link))

    refs = discover_file_references(_document(root))

    assert {r.referencing_tag for r in refs} == {"graphic", "supplementary-material", "ext-link"}


def test_no_references_found_returns_empty_tuple() -> None:
    root = ParsedElement(
        tag="body", namespace_uri=None, children=(ParsedElement(tag="p", namespace_uri=None),)
    )

    refs = discover_file_references(_document(root))

    assert refs == ()


def test_does_not_assign_any_category_to_a_reference() -> None:
    # Explicit negative test for the "no business interpretation" boundary:
    # the FileReference type itself has no category/kind field to assign.
    graphic = ParsedElement(
        tag="graphic",
        namespace_uri=None,
        attributes=(
            ParsedAttribute(name="href", namespace_uri=XLINK_NAMESPACE_URI, value="fig1.jpg"),
        ),
    )
    refs = discover_file_references(
        _document(ParsedElement(tag="body", namespace_uri=None, children=(graphic,)))
    )

    assert not hasattr(refs[0], "category")
    assert not hasattr(refs[0], "kind")


def test_custom_reference_attributes_can_be_supplied() -> None:
    element = ParsedElement(
        tag="link",
        namespace_uri=None,
        attributes=(ParsedAttribute(name="target", namespace_uri=None, value="custom.txt"),),
    )
    root = ParsedElement(tag="body", namespace_uri=None, children=(element,))

    refs = discover_file_references(_document(root), reference_attributes=((None, "target"),))

    assert len(refs) == 1
    assert refs[0].value == "custom.txt"
