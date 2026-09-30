"""Unit tests for meca_engine.extraction.parsed_model."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from meca_engine.extraction.parsed_model import (
    DiagnosticCategory,
    DiagnosticSeverity,
    DoctypeDeclaration,
    EncodingInfo,
    NamespaceDeclaration,
    ParsedAttribute,
    ParsedDocument,
    ParsedElement,
    ParseDiagnostic,
    SourceLocation,
)

pytestmark = pytest.mark.unit


def test_parsed_element_defaults_are_empty() -> None:
    element = ParsedElement(tag="root", namespace_uri=None)

    assert element.attributes == ()
    assert element.children == ()
    assert element.text is None
    assert element.tail is None


def test_parsed_element_is_frozen() -> None:
    element = ParsedElement(tag="root", namespace_uri=None)

    with pytest.raises(dataclasses.FrozenInstanceError):
        element.tag = "changed"  # type: ignore[misc]


def test_parsed_element_preserves_nested_children() -> None:
    child = ParsedElement(tag="child", namespace_uri=None, text="hello")
    parent = ParsedElement(tag="parent", namespace_uri=None, children=(child,))

    assert parent.children[0].tag == "child"
    assert parent.children[0].text == "hello"


def test_parsed_attribute_is_frozen() -> None:
    attribute = ParsedAttribute(name="id", namespace_uri=None, value="x1")

    with pytest.raises(dataclasses.FrozenInstanceError):
        attribute.value = "changed"  # type: ignore[misc]


def test_namespace_declaration_supports_default_namespace() -> None:
    declaration = NamespaceDeclaration(prefix=None, uri="https://example.org/ns")

    assert declaration.prefix is None
    assert declaration.uri == "https://example.org/ns"


def test_doctype_declaration_fields() -> None:
    doctype = DoctypeDeclaration(
        name="article", public_id="-//X//Y//EN", system_id="x.dtd", has_internal_subset=False
    )

    assert doctype.name == "article"
    assert doctype.public_id == "-//X//Y//EN"
    assert doctype.system_id == "x.dtd"
    assert doctype.has_internal_subset is False


def test_encoding_info_fields() -> None:
    info = EncodingInfo(declared_encoding="UTF-8", bom_encoding=None, effective_encoding="UTF-8")

    assert info.declared_encoding == "UTF-8"
    assert info.bom_encoding is None
    assert info.effective_encoding == "UTF-8"


def test_source_location_is_frozen() -> None:
    location = SourceLocation(line=3, column=10)

    with pytest.raises(dataclasses.FrozenInstanceError):
        location.line = 4  # type: ignore[misc]


def test_parse_diagnostic_defaults_location_to_none() -> None:
    diagnostic = ParseDiagnostic(
        severity=DiagnosticSeverity.WARNING,
        category=DiagnosticCategory.ENCODING,
        message="something",
    )

    assert diagnostic.location is None


def test_parsed_document_defaults_are_empty() -> None:
    root = ParsedElement(tag="root", namespace_uri=None)
    document = ParsedDocument(
        source_path=Path("/tmp/x.xml"),
        encoding=EncodingInfo(
            declared_encoding=None, bom_encoding=None, effective_encoding="utf-8"
        ),
        doctype=None,
        root=root,
    )

    assert document.namespace_declarations == ()
    assert document.diagnostics == ()
    assert document.doctype is None


def test_diagnostic_severity_values() -> None:
    assert {s.value for s in DiagnosticSeverity} == {"info", "warning", "error"}


def test_diagnostic_category_values() -> None:
    assert {c.value for c in DiagnosticCategory} == {
        "encoding",
        "doctype",
        "namespace",
        "unsupported_construct",
        "missing_reference",
        "duplicate_id",
        "missing_required_value",
    }
