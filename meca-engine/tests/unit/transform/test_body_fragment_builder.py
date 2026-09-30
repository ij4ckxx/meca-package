"""Unit tests for meca_engine.transform.body_fragment_builder."""

from __future__ import annotations

from pathlib import Path

import pytest

from meca_engine.extraction.navigation import XML_NAMESPACE_URI
from meca_engine.extraction.parsed_model import (
    EncodingInfo,
    NamespaceDeclaration,
    ParsedAttribute,
    ParsedDocument,
    ParsedElement,
)
from meca_engine.transform.body_fragment_builder import build_body_fragment

pytestmark = pytest.mark.unit

_ENCODING = EncodingInfo(declared_encoding=None, bom_encoding=None, effective_encoding="utf-8")
_XLINK_URI = "http://www.w3.org/1999/xlink"


def _document(
    root: ParsedElement, namespace_declarations: tuple[NamespaceDeclaration, ...] = ()
) -> ParsedDocument:
    return ParsedDocument(
        source_path=Path("test.xml"),
        encoding=_ENCODING,
        doctype=None,
        root=root,
        namespace_declarations=namespace_declarations,
    )


def test_serializes_simple_body_with_text() -> None:
    body = ParsedElement(
        tag="body",
        namespace_uri=None,
        children=(ParsedElement(tag="p", namespace_uri=None, text="Hello"),),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(body,))

    fragment = build_body_fragment(_document(root))

    assert fragment.raw_xml_fragment == "<body><p>Hello</p></body>"


def test_serializes_attributes() -> None:
    body = ParsedElement(
        tag="body",
        namespace_uri=None,
        attributes=(ParsedAttribute("id", None, "b1"),),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(body,))

    fragment = build_body_fragment(_document(root))

    assert fragment.raw_xml_fragment == '<body id="b1"/>'


def test_serializes_mixed_content_with_tail() -> None:
    bold = ParsedElement(tag="bold", namespace_uri=None, text="bold", tail=" tail text")
    body = ParsedElement(
        tag="body",
        namespace_uri=None,
        children=(ParsedElement(tag="p", namespace_uri=None, text="a ", children=(bold,)),),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(body,))

    fragment = build_body_fragment(_document(root))

    assert fragment.raw_xml_fragment == "<body><p>a <bold>bold</bold> tail text</p></body>"


def test_escapes_special_characters_in_text_and_attributes() -> None:
    body = ParsedElement(
        tag="body",
        namespace_uri=None,
        attributes=(ParsedAttribute("data-note", None, 'a "quoted" & <thing>'),),
        text="A & B < C",
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(body,))

    fragment = build_body_fragment(_document(root))

    assert "A &amp; B &lt; C" in fragment.raw_xml_fragment
    assert "&amp;" in fragment.raw_xml_fragment
    assert "&lt;thing&gt;" in fragment.raw_xml_fragment


def test_empty_element_is_self_closing() -> None:
    body = ParsedElement(
        tag="body",
        namespace_uri=None,
        children=(ParsedElement(tag="graphic", namespace_uri=None),),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(body,))

    fragment = build_body_fragment(_document(root))

    assert fragment.raw_xml_fragment == "<body><graphic/></body>"


def test_missing_body_produces_empty_fragment() -> None:
    root = ParsedElement(tag="article", namespace_uri=None)

    fragment = build_body_fragment(_document(root))

    assert fragment.raw_xml_fragment == ""


# --- Milestone 6C regression: namespace-prefixed attribute/element preservation ---


def test_prefixed_attribute_reconstructs_declared_prefix() -> None:
    body = ParsedElement(
        tag="body",
        namespace_uri=None,
        children=(
            ParsedElement(
                tag="graphic",
                namespace_uri=None,
                attributes=(ParsedAttribute("href", _XLINK_URI, "fig1.jpg"),),
            ),
        ),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(body,))
    document = _document(root, (NamespaceDeclaration(prefix="xlink", uri=_XLINK_URI),))

    fragment = build_body_fragment(document)

    assert fragment.raw_xml_fragment == '<body><graphic xlink:href="fig1.jpg"/></body>'


def test_multiple_prefixed_attributes_on_the_same_element() -> None:
    body = ParsedElement(
        tag="body",
        namespace_uri=None,
        children=(
            ParsedElement(
                tag="graphic",
                namespace_uri=None,
                attributes=(
                    ParsedAttribute("href", _XLINK_URI, "fig1.jpg"),
                    ParsedAttribute("title", _XLINK_URI, "Figure 1"),
                ),
            ),
        ),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(body,))
    document = _document(root, (NamespaceDeclaration(prefix="xlink", uri=_XLINK_URI),))

    fragment = build_body_fragment(document)

    assert 'xlink:href="fig1.jpg"' in fragment.raw_xml_fragment
    assert 'xlink:title="Figure 1"' in fragment.raw_xml_fragment


def test_prefixed_element_tag_reconstructs_declared_prefix() -> None:
    mml_uri = "http://www.w3.org/1998/Math/MathML"
    body = ParsedElement(
        tag="body",
        namespace_uri=None,
        children=(ParsedElement(tag="math", namespace_uri=mml_uri),),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(body,))
    document = _document(root, (NamespaceDeclaration(prefix="mml", uri=mml_uri),))

    fragment = build_body_fragment(document)

    assert fragment.raw_xml_fragment == "<body><mml:math/></body>"


def test_reserved_xml_prefix_is_always_available_without_a_declaration() -> None:
    body = ParsedElement(
        tag="body",
        namespace_uri=None,
        children=(
            ParsedElement(
                tag="p",
                namespace_uri=None,
                attributes=(ParsedAttribute("lang", XML_NAMESPACE_URI, "en"),),
                text="Text",
            ),
        ),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(body,))

    fragment = build_body_fragment(_document(root))

    assert '<p xml:lang="en">Text</p>' in fragment.raw_xml_fragment


def test_unprefixed_namespace_uri_with_no_declaration_falls_back_to_local_name() -> None:
    unknown_uri = "urn:example:unknown"
    body = ParsedElement(
        tag="body",
        namespace_uri=None,
        children=(
            ParsedElement(
                tag="graphic",
                namespace_uri=None,
                attributes=(ParsedAttribute("href", unknown_uri, "fig1.jpg"),),
            ),
        ),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(body,))

    fragment = build_body_fragment(_document(root))

    assert fragment.raw_xml_fragment == '<body><graphic href="fig1.jpg"/></body>'


def test_default_namespace_declaration_is_not_usable_as_a_prefix() -> None:
    default_uri = "urn:example:default"
    body = ParsedElement(
        tag="body",
        namespace_uri=None,
        children=(
            ParsedElement(
                tag="graphic",
                namespace_uri=None,
                attributes=(ParsedAttribute("href", default_uri, "fig1.jpg"),),
            ),
        ),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(body,))
    document = _document(root, (NamespaceDeclaration(prefix=None, uri=default_uri),))

    fragment = build_body_fragment(document)

    assert fragment.raw_xml_fragment == '<body><graphic href="fig1.jpg"/></body>'


def test_first_declared_prefix_wins_for_a_duplicated_uri() -> None:
    body = ParsedElement(
        tag="body",
        namespace_uri=None,
        children=(
            ParsedElement(
                tag="graphic",
                namespace_uri=None,
                attributes=(ParsedAttribute("href", _XLINK_URI, "fig1.jpg"),),
            ),
        ),
    )
    root = ParsedElement(tag="article", namespace_uri=None, children=(body,))
    document = _document(
        root,
        (
            NamespaceDeclaration(prefix="xlink", uri=_XLINK_URI),
            NamespaceDeclaration(prefix="xl", uri=_XLINK_URI),
        ),
    )

    fragment = build_body_fragment(document)

    assert 'xlink:href="fig1.jpg"' in fragment.raw_xml_fragment
