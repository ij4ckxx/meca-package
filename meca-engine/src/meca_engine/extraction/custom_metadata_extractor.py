"""Custom-metadata extraction — Milestone 4 (extended in Milestone 5B).

Reads every ``custom-meta`` entry out of a
:class:`~meca_engine.extraction.parsed_model.ParsedDocument`, unfiltered
and unclassified — including the ``<custom-meta>`` element's own
attributes (Milestone 5B addition; see
:class:`~meca_engine.extraction.metadata_models.CustomMetaEntry`). A pure
function: no logging, no I/O, no exceptions for missing fields.
Business-rule-driven filtering (the deny-list logic in the Business Rule
Book) is explicitly deferred to
:mod:`meca_engine.extraction.custom_meta_classifier`, built on top of
this extraction — this function extracts everything it finds, without
judgment.

**``named-content`` content-type attribute tolerance (Milestone 9
correction)**: confirmed via real production packages that this
concept's attribute is not always spelled ``content-type`` — some
source packages spell it ``data-type`` instead, for the identical
concept. :func:`_resolve_content_type` tries ``content-type`` first
(preserving every previously-processed package's exact behavior) and
falls back to ``data-type`` only when ``content-type`` is absent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.extraction.metadata_models import (
    CustomMetadata,
    CustomMetaEntry,
    NamedContentField,
)
from meca_engine.extraction.navigation import find_all, find_first, get_attribute, get_text

if TYPE_CHECKING:
    from meca_engine.extraction.parsed_model import ParsedDocument, ParsedElement, ParseDiagnostic


def _resolve_content_type(element: ParsedElement) -> str | None:
    """Read a ``named-content`` element's content-type, tolerating both attribute spellings.

    Real Kriyadocs source packages have been observed using two distinct,
    equally-valid attribute names for the same concept: ``content-type``
    (the originally-observed convention) and ``data-type`` (confirmed
    present, in place of ``content-type``, in later-observed packages).
    ``content-type`` is checked first so every previously-processed
    package's behavior is completely unchanged; ``data-type`` is tried
    only when ``content-type`` is absent.
    """
    content_type = get_attribute(element, "content-type")
    if content_type is not None:
        return content_type
    return get_attribute(element, "data-type")


def _extract_named_content(value_element: ParsedElement) -> tuple[NamedContentField, ...]:
    return tuple(
        NamedContentField(
            content_type=_resolve_content_type(element),
            text=get_text(element, recursive=True),
        )
        for element in find_all(value_element, "named-content")
    )


def _extract_attributes(element: ParsedElement) -> tuple[tuple[str, str], ...]:
    return tuple(
        (attribute.name, attribute.value)
        for attribute in element.attributes
        if attribute.namespace_uri is None
    )


def _extract_entry(element: ParsedElement) -> CustomMetaEntry:
    name_element = find_first(element, "meta-name")
    value_element = find_first(element, "meta-value")
    name = get_text(name_element, recursive=True) if name_element is not None else None
    value_text = get_text(value_element, recursive=True) if value_element is not None else ""
    named_content = _extract_named_content(value_element) if value_element is not None else ()
    return CustomMetaEntry(
        name=name,
        value_text=value_text,
        named_content=named_content,
        attributes=_extract_attributes(element),
    )


def extract_custom_metadata(
    document: ParsedDocument,
) -> tuple[CustomMetadata, tuple[ParseDiagnostic, ...]]:
    """Extract every custom-metadata entry from a parsed document.

    Args:
        document: The parsed document to read from.

    Returns:
        The extracted
        :class:`~meca_engine.extraction.metadata_models.CustomMetadata`,
        alongside an always-empty diagnostics tuple. Every ``custom-meta``
        entry found is included, unfiltered.
    """
    entries = tuple(_extract_entry(element) for element in find_all(document.root, "custom-meta"))
    return CustomMetadata(entries=entries), ()
