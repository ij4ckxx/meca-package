"""Unit tests for meca_engine.generators.xml.helpers."""

from __future__ import annotations

import re
from datetime import date

import pytest

from meca_engine.generators.xml.builder import XmlDocumentBuilder
from meca_engine.generators.xml.helpers import (
    add_optional_element,
    add_repeated_elements,
    append_mixed_text,
    escape_text,
    format_year_month_day,
    parse_fragment_with_namespaces,
    preserve_whitespace,
    strip_attribute,
    strip_attribute_matching,
    strip_characters,
    uses_prefix,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def builder() -> XmlDocumentBuilder:
    return XmlDocumentBuilder()


def test_add_optional_element_creates_element_when_value_present(
    builder: XmlDocumentBuilder,
) -> None:
    root = builder.create_root("article-meta")

    element = add_optional_element(builder, root, "copyright-year", "2025")

    assert element is not None
    assert element.text == "2025"
    assert list(root) == [element]


def test_add_optional_element_returns_none_when_value_is_none(
    builder: XmlDocumentBuilder,
) -> None:
    root = builder.create_root("article-meta")

    element = add_optional_element(builder, root, "copyright-year", None)

    assert element is None
    assert list(root) == []


def test_add_optional_element_returns_none_when_value_is_empty_string(
    builder: XmlDocumentBuilder,
) -> None:
    root = builder.create_root("article-meta")

    element = add_optional_element(builder, root, "copyright-year", "")

    assert element is None
    assert list(root) == []


def test_add_repeated_elements_creates_one_per_value_in_order(
    builder: XmlDocumentBuilder,
) -> None:
    root = builder.create_root("kwd-group")

    elements = add_repeated_elements(builder, root, "kwd", ["oncology", "genomics"])

    assert [e.text for e in elements] == ["oncology", "genomics"]
    assert list(root) == list(elements)


def test_add_repeated_elements_with_empty_values_creates_nothing(
    builder: XmlDocumentBuilder,
) -> None:
    root = builder.create_root("kwd-group")

    elements = add_repeated_elements(builder, root, "kwd", [])

    assert elements == ()
    assert list(root) == []


def test_add_repeated_elements_applies_shared_attributes(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("history")

    elements = add_repeated_elements(
        builder, root, "date", ["2025-01-01"], attributes_for={"date-type": "received"}
    )

    assert elements[0].get("date-type") == "received"


def test_append_mixed_text_sets_element_text_when_no_children(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("p")

    append_mixed_text(root, "leading text")

    assert root.text == "leading text"


def test_append_mixed_text_appends_to_existing_text(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("p")
    root.text = "start "

    append_mixed_text(root, "end")

    assert root.text == "start end"


def test_append_mixed_text_sets_last_child_tail_when_children_exist(
    builder: XmlDocumentBuilder,
) -> None:
    root = builder.create_root("p")
    builder.create_element(root, "xref", text="Figure 1")

    append_mixed_text(root, " trailing text")

    assert list(root)[-1].tail == " trailing text"


def test_append_mixed_text_appends_to_existing_tail(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("p")
    child = builder.create_element(root, "xref", text="Figure 1")
    child.tail = "and "

    append_mixed_text(root, "more")

    assert child.tail == "and more"


def test_preserve_whitespace_sets_xml_space_attribute(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("pre")

    preserve_whitespace(root)

    assert root.get("xml:space") == "preserve"


def test_escape_text_escapes_significant_characters() -> None:
    assert escape_text("a < b & c > d") == "a &lt; b &amp; c &gt; d"


def test_escape_text_leaves_plain_text_unchanged() -> None:
    assert escape_text("plain text") == "plain text"


def test_format_year_month_day_zero_pads_single_digit_values() -> None:
    assert format_year_month_day(date(2025, 1, 5)) == ("2025", "01", "05")


def test_format_year_month_day_preserves_two_digit_values() -> None:
    assert format_year_month_day(date(2025, 12, 25)) == ("2025", "12", "25")


def test_strip_characters_removes_every_occurrence() -> None:
    assert strip_characters("10-1042-2025", "-") == "1010422025"


def test_strip_characters_removes_multiple_distinct_characters() -> None:
    assert strip_characters("a-b_c-d", "-_") == "abcd"


def test_strip_characters_with_no_matches_returns_original() -> None:
    assert strip_characters("abcd", "-_") == "abcd"


def test_strip_characters_with_empty_characters_returns_original() -> None:
    assert strip_characters("abcd", "") == "abcd"


# --- parse_fragment_with_namespaces --------------------------------------------

_XLINK_URI = "http://www.w3.org/1999/xlink"
_MML_URI = "http://www.w3.org/1998/Math/MathML"
_DECLARATIONS = {"xmlns:xlink": _XLINK_URI, "xmlns:mml": _MML_URI}


def test_parse_fragment_with_namespaces_resolves_prefixed_attribute() -> None:
    element = parse_fragment_with_namespaces('<graphic xlink:href="fig1.jpg"/>', _DECLARATIONS)

    assert element.tag == "graphic"
    assert element.get("xlink:href") == "fig1.jpg"


def test_parse_fragment_with_namespaces_resolves_prefixed_element_tag() -> None:
    element = parse_fragment_with_namespaces("<mml:math/>", _DECLARATIONS)

    assert element.tag == "mml:math"


def test_parse_fragment_with_namespaces_resolves_nested_descendants() -> None:
    element = parse_fragment_with_namespaces(
        '<p><graphic xlink:href="fig1.jpg"/></p>', _DECLARATIONS
    )

    child = element.find("graphic")
    assert child is not None
    assert child.get("xlink:href") == "fig1.jpg"


def test_parse_fragment_with_namespaces_leaves_unprefixed_content_unchanged() -> None:
    element = parse_fragment_with_namespaces('<p id="p1">text</p>', _DECLARATIONS)

    assert element.tag == "p"
    assert element.get("id") == "p1"
    assert element.text == "text"


def test_parse_fragment_with_namespaces_falls_back_for_the_reserved_xml_prefix() -> None:
    # The "xml:" prefix is implicitly available in every XML document
    # (per the XML Namespaces spec) without needing an explicit `xmlns:xml`
    # declaration — ElementTree parses `xml:lang` successfully even though
    # the caller's own `namespace_declarations` never mentioned it. This
    # helper has no way to know which prefix the source document itself
    # used for it, so it falls back to the unprefixed local name — a
    # documented, non-blocking residual gap (see the module docstring).
    element = parse_fragment_with_namespaces('<p xml:lang="en">text</p>', _DECLARATIONS)

    assert element.get("lang") == "en"
    assert element.get("xml:lang") is None


# --- strip_attribute ------------------------------------------------------------


def test_strip_attribute_removes_from_root_and_descendants(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article", attributes={"id": "a1"})
    child = builder.create_element(root, "p", attributes={"id": "p1", "class": "note"})

    strip_attribute(root, "id")

    assert root.get("id") is None
    assert child.get("id") is None
    assert child.get("class") == "note"


def test_strip_attribute_is_a_no_op_when_attribute_absent(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")

    strip_attribute(root, "id")  # must not raise

    assert root.attrib == {}


# --- strip_attribute_matching ----------------------------------------------------

_UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)


def test_strip_attribute_matching_removes_only_matching_values(
    builder: XmlDocumentBuilder,
) -> None:
    root = builder.create_root("article")
    uuid_child = builder.create_element(
        root, "p", attributes={"id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
    )
    semantic_child = builder.create_element(root, "aff", attributes={"id": "aff1"})

    strip_attribute_matching(root, "id", _UUID_PATTERN)

    assert uuid_child.get("id") is None
    assert semantic_child.get("id") == "aff1"


def test_strip_attribute_matching_is_a_no_op_when_attribute_absent(
    builder: XmlDocumentBuilder,
) -> None:
    root = builder.create_root("article")

    strip_attribute_matching(root, "id", _UUID_PATTERN)  # must not raise

    assert root.attrib == {}


# --- uses_prefix ------------------------------------------------------------------


def test_uses_prefix_true_for_prefixed_attribute(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")
    builder.create_element(root, "email", attributes={"xlink:href": "a@example.com"})

    assert uses_prefix(root, "xlink") is True


def test_uses_prefix_true_for_prefixed_element_tag(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")
    builder.create_element(root, "mml:math")

    assert uses_prefix(root, "mml") is True


def test_uses_prefix_false_when_prefix_never_appears(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")
    builder.create_element(root, "p", attributes={"id": "p1"})

    assert uses_prefix(root, "xlink") is False
