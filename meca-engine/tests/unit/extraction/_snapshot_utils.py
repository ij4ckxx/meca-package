"""Test-only helper: serialize a ParsedDocument into a JSON-comparable dict.

Not a test module itself (no ``test_`` prefix — pytest will not collect
it). Used by ``test_golden_snapshots.py`` to compare a freshly-parsed
document's structure against a checked-in golden JSON file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from meca_engine.extraction.parsed_model import (
        ParsedAttribute,
        ParsedDocument,
        ParsedElement,
    )


def attribute_to_dict(attribute: ParsedAttribute) -> dict[str, Any]:
    """Convert one ParsedAttribute to a JSON-safe dict."""
    return {
        "name": attribute.name,
        "namespace_uri": attribute.namespace_uri,
        "value": attribute.value,
    }


def element_to_dict(element: ParsedElement) -> dict[str, Any]:
    """Recursively convert one ParsedElement subtree to a JSON-safe dict."""
    return {
        "tag": element.tag,
        "namespace_uri": element.namespace_uri,
        "attributes": [attribute_to_dict(a) for a in element.attributes],
        "children": [element_to_dict(c) for c in element.children],
        "text": element.text,
        "tail": element.tail,
    }


def document_to_snapshot_dict(document: ParsedDocument) -> dict[str, Any]:
    """Convert a ParsedDocument to a JSON-safe, order-stable dict for snapshotting.

    Deliberately excludes ``source_path`` (an absolute, environment-specific
    path that would make the snapshot non-portable) and diagnostic
    ``location`` fields (currently always ``None`` — see the XML Loader's
    documented scope decision to not track per-element source positions).
    """
    return {
        "encoding": {
            "declared_encoding": document.encoding.declared_encoding,
            "bom_encoding": document.encoding.bom_encoding,
            "effective_encoding": document.encoding.effective_encoding,
        },
        "doctype": (
            {
                "name": document.doctype.name,
                "public_id": document.doctype.public_id,
                "system_id": document.doctype.system_id,
                "has_internal_subset": document.doctype.has_internal_subset,
            }
            if document.doctype is not None
            else None
        ),
        "root": element_to_dict(document.root),
        "namespace_declarations": [
            {"prefix": d.prefix, "uri": d.uri} for d in document.namespace_declarations
        ],
        "diagnostics": [
            {"severity": d.severity.value, "category": d.category.value, "message": d.message}
            for d in document.diagnostics
        ],
    }
