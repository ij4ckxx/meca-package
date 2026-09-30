"""Unit tests for meca_engine.extraction.diagnostics."""

from __future__ import annotations

import pytest

from meca_engine.extraction.diagnostics import (
    find_dangling_references,
    find_duplicate_ids,
    find_malformed_references,
)
from meca_engine.extraction.parsed_model import DiagnosticCategory, ParsedAttribute, ParsedElement

pytestmark = pytest.mark.unit


def test_finds_no_dangling_references_when_all_resolve() -> None:
    aff = ParsedElement(
        tag="aff", namespace_uri=None, attributes=(ParsedAttribute("id", None, "aff1"),)
    )
    xref = ParsedElement(
        tag="xref", namespace_uri=None, attributes=(ParsedAttribute("rid", None, "aff1"),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(aff, xref))

    diagnostics = find_dangling_references(root)

    assert diagnostics == ()


def test_finds_a_dangling_reference() -> None:
    xref = ParsedElement(
        tag="xref", namespace_uri=None, attributes=(ParsedAttribute("rid", None, "missing"),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(xref,))

    diagnostics = find_dangling_references(root)

    assert len(diagnostics) == 1
    assert diagnostics[0].category is DiagnosticCategory.MISSING_REFERENCE
    assert "missing" in diagnostics[0].message
    assert "xref" in diagnostics[0].message


def test_handles_multiple_space_separated_reference_tokens() -> None:
    aff1 = ParsedElement(
        tag="aff", namespace_uri=None, attributes=(ParsedAttribute("id", None, "aff1"),)
    )
    xref = ParsedElement(
        tag="xref", namespace_uri=None, attributes=(ParsedAttribute("rid", None, "aff1 aff2"),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(aff1, xref))

    diagnostics = find_dangling_references(root)

    assert len(diagnostics) == 1
    assert "aff2" in diagnostics[0].message


def test_custom_reference_attribute_names() -> None:
    element = ParsedElement(
        tag="link", namespace_uri=None, attributes=(ParsedAttribute("target-id", None, "missing"),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(element,))

    diagnostics = find_dangling_references(root, reference_attribute_names=("target-id",))

    assert len(diagnostics) == 1


def test_default_reference_attribute_name_is_rid_only() -> None:
    element = ParsedElement(
        tag="link", namespace_uri=None, attributes=(ParsedAttribute("target-id", None, "missing"),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(element,))

    diagnostics = find_dangling_references(root)  # default only checks "rid"

    assert diagnostics == ()


def test_ignores_namespaced_attributes_with_matching_local_name() -> None:
    element = ParsedElement(
        tag="link", namespace_uri=None, attributes=(ParsedAttribute("rid", "urn:other", "missing"),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(element,))

    diagnostics = find_dangling_references(root)

    assert diagnostics == ()


def test_empty_document_produces_no_diagnostics() -> None:
    root = ParsedElement(tag="root", namespace_uri=None)

    assert find_dangling_references(root) == ()


def test_find_duplicate_ids_flags_the_repeat_only() -> None:
    first = ParsedElement(
        tag="aff", namespace_uri=None, attributes=(ParsedAttribute("id", None, "x1"),)
    )
    second = ParsedElement(
        tag="fig", namespace_uri=None, attributes=(ParsedAttribute("id", None, "x1"),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(first, second))

    diagnostics = find_duplicate_ids(root)

    assert len(diagnostics) == 1
    assert diagnostics[0].category is DiagnosticCategory.DUPLICATE_ID
    assert "fig" in diagnostics[0].message
    assert "x1" in diagnostics[0].message


def test_find_duplicate_ids_no_repeat_produces_no_diagnostics() -> None:
    first = ParsedElement(
        tag="aff", namespace_uri=None, attributes=(ParsedAttribute("id", None, "x1"),)
    )
    second = ParsedElement(
        tag="fig", namespace_uri=None, attributes=(ParsedAttribute("id", None, "x2"),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(first, second))

    assert find_duplicate_ids(root) == ()


def test_find_duplicate_ids_recognizes_xml_id() -> None:
    xml_ns = "http://www.w3.org/XML/1998/namespace"
    first = ParsedElement(
        tag="aff", namespace_uri=None, attributes=(ParsedAttribute("id", xml_ns, "x1"),)
    )
    second = ParsedElement(
        tag="fig", namespace_uri=None, attributes=(ParsedAttribute("id", xml_ns, "x1"),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(first, second))

    diagnostics = find_duplicate_ids(root)

    assert len(diagnostics) == 1


def test_find_malformed_references_flags_empty_value() -> None:
    element = ParsedElement(
        tag="xref", namespace_uri=None, attributes=(ParsedAttribute("rid", None, ""),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(element,))

    diagnostics = find_malformed_references(root)

    assert len(diagnostics) == 1
    assert diagnostics[0].category is DiagnosticCategory.MISSING_REQUIRED_VALUE
    assert "xref" in diagnostics[0].message


def test_find_malformed_references_flags_whitespace_only_value() -> None:
    element = ParsedElement(
        tag="xref", namespace_uri=None, attributes=(ParsedAttribute("rid", None, "   "),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(element,))

    assert len(find_malformed_references(root)) == 1


def test_find_malformed_references_ignores_populated_value() -> None:
    element = ParsedElement(
        tag="xref", namespace_uri=None, attributes=(ParsedAttribute("rid", None, "aff1"),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(element,))

    assert find_malformed_references(root) == ()
