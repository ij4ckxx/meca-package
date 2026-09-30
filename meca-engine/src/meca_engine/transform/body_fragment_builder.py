"""Body fragment construction — Milestone 5B.

Builds :class:`~meca_engine.model.article.BodyFragment` by serializing the
parsed document's ``<body>`` subtree back into an XML text fragment.

**Not "XML generation"** in this milestone's excluded sense (that phrase
refers to the 5 output documents — raw.xml/article.xml/manifest.xml/
reviews.xml/transfer.xml — a later milestone's job): this is a
structure-preserving copy of already-parsed content into the one ICAM
field the LLD describes as "copied verbatim byte-for-byte" (11_LLD_02...
§3.2), with no business rule, no value transformation, and no synthesis
of any content that wasn't already in the parsed tree.

**Documented fidelity limitation**: true byte-for-byte reproduction is
not achievable from this milestone's inputs — Milestone 3's
:class:`~meca_engine.extraction.parsed_model.ParsedDocument` is a
structured tree, not the original source bytes (which are discarded
after parsing; see `extraction.xml_loader`). This serializer reconstructs
well-formed XML text from that tree (tag/attribute/text/tail, escaped),
which is faithful to the parsed structure but is not guaranteed to be
byte-identical to the original source formatting (whitespace-only
differences, attribute ordering, self-closing-tag style).

**Milestone 6C fix (prerequisite correction)**: a namespace-prefixed
tag/attribute (e.g. a source ``<graphic xlink:href="...">``) was
previously reserialized with its prefix silently dropped
(``<graphic href="...">``) — :class:`~meca_engine.extraction.parsed_model.ParsedAttribute`/
:class:`~meca_engine.extraction.parsed_model.ParsedElement` split a
prefixed name into ``name`` (local part) and ``namespace_uri``
separately, and this serializer only ever read ``name``. Confirmed via
direct inspection of CS-2025-8493_C's body (`xlink:href`/`xlink:title`
on `<graphic>`-family elements) and by the Milestone 6B raw.xml Golden
Comparison Report, which first surfaced the defect. Fixed by
reconstructing each prefix from
:attr:`~meca_engine.extraction.parsed_model.ParsedDocument.namespace_declarations`
— the *source document's own* ``xmlns:*`` bindings, captured at parse
time (Milestone 3) — never a hard-coded prefix table; the reserved
``xml:`` prefix (XML Namespaces spec, never declared via an explicit
``xmlns:xml`` attribute) is the one exception, seeded directly since no
document ever declares it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from xml.sax.saxutils import escape, quoteattr

from meca_engine.extraction.navigation import XML_NAMESPACE_URI, find_first
from meca_engine.model.article import BodyFragment

if TYPE_CHECKING:
    from collections.abc import Mapping

    from meca_engine.extraction.parsed_model import (
        NamespaceDeclaration,
        ParsedDocument,
        ParsedElement,
    )

_BODY_TAG = "body"
_XML_PREFIX = "xml"


def build_body_fragment(document: ParsedDocument) -> BodyFragment:
    """Build the article's body fragment from its parsed ``<body>`` element.

    Args:
        document: The parsed document to read from.

    Returns:
        The built :class:`~meca_engine.model.article.BodyFragment`. An
        empty fragment (``""``) when the document has no ``<body>``
        element — a structural fact for a later validation stage to
        flag, not this transformer's concern.
    """
    body_element = find_first(document.root, _BODY_TAG)
    if body_element is None:
        return BodyFragment(raw_xml_fragment="")
    prefix_by_uri = _build_prefix_lookup(document.namespace_declarations)
    return BodyFragment(raw_xml_fragment=_serialize_element(body_element, prefix_by_uri))


def _build_prefix_lookup(
    declarations: tuple[NamespaceDeclaration, ...],
) -> dict[str, str]:
    """Map namespace URI to prefix, from the source document's own ``xmlns:*`` declarations.

    The first-declared prefix wins for a given URI (deterministic; matches
    how the source document itself resolves it). A default-namespace
    declaration (``prefix is None``) cannot qualify a prefixed name and is
    skipped. The reserved ``xml:`` prefix is seeded unconditionally — the
    XML Namespaces spec binds it to every document implicitly, so no
    source document ever declares it via an ``xmlns:xml`` attribute.
    """
    lookup: dict[str, str] = {XML_NAMESPACE_URI: _XML_PREFIX}
    for declaration in declarations:
        if declaration.prefix is not None and declaration.uri not in lookup:
            lookup[declaration.uri] = declaration.prefix
    return lookup


def _qualify(name: str, namespace_uri: str | None, prefix_by_uri: Mapping[str, str]) -> str:
    if namespace_uri is None:
        return name
    prefix = prefix_by_uri.get(namespace_uri)
    if prefix is None:
        # No declared prefix for this URI anywhere in the source document
        # — cannot invent one; falls back to the unprefixed local name
        # (the pre-fix behavior), a documented, non-blocking residual gap
        # for a namespace URI the source itself never named.
        return name
    return f"{prefix}:{name}"


def _serialize_element(element: ParsedElement, prefix_by_uri: Mapping[str, str]) -> str:
    tag = _qualify(element.tag, element.namespace_uri, prefix_by_uri)
    attributes = "".join(
        f" {_qualify(attribute.name, attribute.namespace_uri, prefix_by_uri)}="
        f"{quoteattr(attribute.value)}"
        for attribute in element.attributes
    )
    if not element.children and not element.text:
        opening = f"<{tag}{attributes}/>"
        return opening + (escape(element.tail) if element.tail else "")

    inner = escape(element.text) if element.text else ""
    inner += "".join(_serialize_element(child, prefix_by_uri) for child in element.children)
    opening_closing = f"<{tag}{attributes}>{inner}</{tag}>"
    return opening_closing + (escape(element.tail) if element.tail else "")
