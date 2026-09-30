"""Unit tests for meca_engine.extraction.cross_reference_extractor."""

from __future__ import annotations

from pathlib import Path

import pytest

from meca_engine.extraction.cross_reference_extractor import extract_cross_references
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


def test_builds_compact_id_index() -> None:
    aff = ParsedElement(
        tag="aff", namespace_uri=None, attributes=(ParsedAttribute("id", None, "aff1"),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(aff,))

    cross_references, diagnostics = extract_cross_references(_document(root))

    assert cross_references.id_index == (("aff1", "aff"),)
    assert diagnostics == ()


def test_extracts_reference_with_ref_type_and_target_ids() -> None:
    xref = ParsedElement(
        tag="xref",
        namespace_uri=None,
        attributes=(
            ParsedAttribute("ref-type", None, "bibr"),
            ParsedAttribute("rid", None, "ref1 ref2"),
        ),
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(xref,))

    cross_references, _ = extract_cross_references(_document(root))

    assert len(cross_references.references) == 1
    ref = cross_references.references[0]
    assert ref.referencing_tag == "xref"
    assert ref.referencing_ref_type == "bibr"
    assert ref.attribute_name == "rid"
    assert ref.target_ids == ("ref1", "ref2")


def test_duplicate_id_produces_diagnostic() -> None:
    first = ParsedElement(
        tag="aff", namespace_uri=None, attributes=(ParsedAttribute("id", None, "x1"),)
    )
    second = ParsedElement(
        tag="fig", namespace_uri=None, attributes=(ParsedAttribute("id", None, "x1"),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(first, second))

    _, diagnostics = extract_cross_references(_document(root))

    assert any(d.category is DiagnosticCategory.DUPLICATE_ID for d in diagnostics)


def test_malformed_reference_produces_diagnostic() -> None:
    xref = ParsedElement(
        tag="xref", namespace_uri=None, attributes=(ParsedAttribute("rid", None, ""),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(xref,))

    _, diagnostics = extract_cross_references(_document(root))

    assert any(d.category is DiagnosticCategory.MISSING_REQUIRED_VALUE for d in diagnostics)


def test_xref_without_a_reference_attribute_is_skipped() -> None:
    xref = ParsedElement(
        tag="xref", namespace_uri=None, attributes=(ParsedAttribute("ref-type", None, "bibr"),)
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(xref,))

    cross_references, _ = extract_cross_references(_document(root))

    assert cross_references.references == ()


def test_empty_document_produces_no_references_or_diagnostics() -> None:
    root = ParsedElement(tag="root", namespace_uri=None)

    cross_references, diagnostics = extract_cross_references(_document(root))

    assert cross_references.id_index == ()
    assert cross_references.references == ()
    assert diagnostics == ()
