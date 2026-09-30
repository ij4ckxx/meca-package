"""XML Helper Library — Generator Framework (Milestone 6A).

Small, reusable, business-logic-free helpers built on top of
:class:`~meca_engine.generators.xml.builder.XmlDocumentBuilder`. Every
function here is a pure structural utility — none of them know what a
``display-channel``, a ``License Type``, or a DOI is; a future
generator's business-rule modules call these, never re-implement
equivalent tree-manipulation or string-formatting logic themselves.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from xml.etree.ElementTree import fromstring, tostring
from xml.sax.saxutils import escape as _sax_escape

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import date
    from xml.etree.ElementTree import Element

    from meca_engine.generators.xml.builder import XmlDocumentBuilder


def add_optional_element(
    builder: XmlDocumentBuilder,
    parent: Element,
    tag: str,
    value: str | None,
    *,
    attributes: Mapping[str, str] | None = None,
) -> Element | None:
    """Append ``tag`` only if ``value`` is present and non-empty.

    Args:
        builder: The document builder to create the element through.
        parent: The element to append to.
        tag: The new element's tag name.
        value: The element's text content — no element is created at all
            when this is ``None`` or ``""``, rather than creating an
            empty element.
        attributes: Attributes to set on the new element, if created.

    Returns:
        The created element, or ``None`` if ``value`` was absent.
    """
    if not value:
        return None
    return builder.create_element(parent, tag, attributes=attributes, text=value)


def add_repeated_elements(
    builder: XmlDocumentBuilder,
    parent: Element,
    tag: str,
    values: Iterable[str],
    *,
    attributes_for: Mapping[str, str] | None = None,
) -> tuple[Element, ...]:
    """Append one ``tag`` element per value in ``values``, in order.

    Args:
        builder: The document builder to create elements through.
        parent: The element to append to.
        tag: The tag name repeated for every value.
        values: The text content for each element, in the exact order
            they should appear.
        attributes_for: Attributes applied identically to every created
            element (a single shared set — a per-value attribute map is
            each generator's own business-rule concern, not this generic
            helper's).

    Returns:
        Every created element, in the order the corresponding values were
        given, as a tuple (never a list — matching this codebase's
        collection-immutability convention).
    """
    return tuple(
        builder.create_element(parent, tag, attributes=attributes_for, text=value)
        for value in values
    )


def append_mixed_text(element: Element, text: str) -> None:
    """Append trailing text to ``element`` without disturbing its children.

    XML mixed content (text interleaved with child elements) is
    represented in :mod:`xml.etree.ElementTree` as each child's
    ``.tail`` — this helper hides that detail: appending after an
    element with no children yet extends its own ``.text``; appending
    after one that already has children extends the last child's
    ``.tail`` instead, exactly matching where the new text will actually
    render in the serialized output.

    Args:
        element: The element to append trailing text to.
        text: The text to append.
    """
    children = list(element)
    if not children:
        element.text = (element.text or "") + text
        return
    last_child = children[-1]
    last_child.tail = (last_child.tail or "") + text


def preserve_whitespace(element: Element) -> None:
    """Mark ``element`` as ``xml:space="preserve"``.

    A structural attribute, not a business decision — callers decide
    which elements need it.
    """
    element.set("xml:space", "preserve")


def escape_text(text: str) -> str:
    """Return ``text`` with XML-significant characters (``&``, ``<``, ``>``) escaped.

    :class:`~meca_engine.generators.xml.builder.XmlDocumentBuilder`
    already escapes every element's text/attribute content automatically
    during serialization — this helper exists only for the rarer case of
    composing a raw text fragment outside the builder's tree (e.g. inside
    a hand-assembled diagnostic message meant to embed literal markup
    safely). Prefer building through the tree wherever possible.
    """
    return _sax_escape(text)


def format_year_month_day(value: date) -> tuple[str, str, str]:
    """Return ``value`` as zero-padded ``(year, month, day)`` strings.

    Matches the ICAM's own date-component convention
    (``meca_engine.model.article.HistoryDates`` et al. store dates as a
    single :class:`datetime.date`; JATS represents a date as separate
    ``<year>``/``<month>``/``<day>`` elements) — a purely structural
    reformatting, no calendar or timezone logic beyond what
    :class:`datetime.date` itself already validated.
    """
    return f"{value.year:04d}", f"{value.month:02d}", f"{value.day:02d}"


def parse_fragment_with_namespaces(
    fragment: str, namespace_declarations: Mapping[str, str]
) -> Element:
    """Parse an XML fragment that uses namespace-prefixed names but declares none itself.

    A fragment produced by re-serializing part of an already-parsed
    document (e.g. an ICAM field holding verbatim source XML text) can
    carry namespace-prefixed tags/attributes (``xlink:href``) with no
    ``xmlns:*`` declaration in scope on its own — :mod:`xml.etree.ElementTree`
    cannot parse that standalone. This wraps the fragment in a throwaway
    element declaring the given namespaces just long enough to parse it,
    then converts every resulting Clark-notation name (``{uri}local``,
    ``ElementTree``'s own internal resolution) back to this framework's
    literal ``prefix:local`` convention — see
    :mod:`meca_engine.generators.xml.namespaces`'s module docstring for
    why Clark notation and ``ET.register_namespace`` are never used
    elsewhere in this codebase.

    Args:
        fragment: The XML fragment text, e.g. ``"<p>...</p>"``.
        namespace_declarations: An ``{"xmlns:prefix": uri, ...}`` mapping,
            typically :meth:`~meca_engine.generators.xml.namespaces.NamespaceManager.declarations`'s
            own return value.

    Returns:
        The parsed fragment's root element, with every tag/attribute name
        already converted back to literal ``prefix:local`` form.
    """
    wrapper_attributes = " ".join(
        f'{name}="{value}"' for name, value in namespace_declarations.items()
    )
    wrapped = f"<meca-wrapper {wrapper_attributes}>{fragment}</meca-wrapper>"
    parsed_element = next(iter(fromstring(wrapped)))
    _delclarkify(parsed_element, _prefix_by_uri(namespace_declarations))
    return parsed_element


def parse_document_with_namespaces(
    document_bytes: bytes, namespace_declarations: Mapping[str, str]
) -> Element:
    """Parse a *complete* XML document (already declaring its own namespaces).

    Unlike :func:`parse_fragment_with_namespaces`, a complete document
    (e.g. one this framework's own
    :meth:`~meca_engine.generators.xml.builder.XmlDocumentBuilder.serialize`
    already produced, with its own ``xmlns:*`` root attributes) needs no
    wrapper — :mod:`xml.etree.ElementTree` parses it directly. But it
    still resolves every namespace-prefixed name into Clark notation
    internally, exactly as :func:`parse_fragment_with_namespaces` does,
    so the same de-Clarkification step applies to the whole parsed tree
    before a generator built on this framework's literal-``prefix:local``
    convention touches it.

    Args:
        document_bytes: The complete, already-serialized document.
        namespace_declarations: The ``{"xmlns:prefix": uri, ...}`` set
            the document itself is known to declare (so Clark-notation
            URIs can be mapped back to their prefixes).

    Returns:
        The parsed document's root element, with every tag/attribute
        name already converted back to literal ``prefix:local`` form.
    """
    root_element = fromstring(document_bytes)
    _delclarkify(root_element, _prefix_by_uri(namespace_declarations))
    return root_element


def _prefix_by_uri(namespace_declarations: Mapping[str, str]) -> dict[str, str]:
    return {
        uri: (name.split(":", 1)[1] if ":" in name else "")
        for name, uri in namespace_declarations.items()
    }


def _delclarkify(element: Element, prefix_by_uri: Mapping[str, str]) -> None:
    element.tag = _resolve_clark_name(element.tag, prefix_by_uri)
    if element.attrib:
        resolved_attributes = {
            _resolve_clark_name(name, prefix_by_uri): value
            for name, value in element.attrib.items()
        }
        element.attrib.clear()
        element.attrib.update(resolved_attributes)
    for child in element:
        _delclarkify(child, prefix_by_uri)


def _resolve_clark_name(name: str, prefix_by_uri: Mapping[str, str]) -> str:
    if not name.startswith("{"):
        return name
    uri, local_name = name[1:].split("}", 1)
    prefix = prefix_by_uri.get(uri)
    return f"{prefix}:{local_name}" if prefix else local_name


def strip_attribute(element: Element, attribute_name: str) -> None:
    """Remove ``attribute_name`` from ``element`` and every descendant, in place.

    A generic structural utility — carries no opinion about *which*
    attribute a business rule strips (e.g. Business Rule Book BR-054's
    ``id`` removal); that decision belongs to the calling generator.
    """
    for descendant in element.iter():
        descendant.attrib.pop(attribute_name, None)


def strip_attribute_matching(
    element: Element, attribute_name: str, pattern: re.Pattern[str]
) -> None:
    """Remove ``attribute_name`` where its value matches ``pattern``, recursively.

    A generic structural utility for "strip this attribute, but only
    when its value looks like *that*" rules (e.g. Business Rule Book
    BR-054, which strips ``id`` only when it is a Kriyadocs-internal
    UUID — a semantic id like ``"aff1"`` used for cross-reference linking
    must survive). Carries no opinion about the pattern itself; that
    decision belongs to the calling generator.
    """
    for descendant in element.iter():
        value = descendant.attrib.get(attribute_name)
        if value is not None and pattern.fullmatch(value):
            del descendant.attrib[attribute_name]


def drop_duplicate_children_by_attribute(element: Element, attribute_name: str) -> list[str]:
    """Remove direct children of ``element`` whose ``attribute_name`` repeats, keeping the first.

    A generic structural utility for source XML that copies the same
    element (same id, same content) more than once — an XML ``ID``-typed
    attribute must be document-unique, so re-emitting a repeated element
    verbatim would produce a DTD-invalid document. Carries no opinion
    about *why* the source repeats it; that's for the calling generator
    to document. Children with no such attribute are never touched.

    A repeated attribute value is only ever dropped when the repeat is
    byte-for-byte identical (compared via serialized content, not just
    the attribute value) — if the same id repeats with different
    content, both are left in place rather than silently discarding one;
    the resulting duplicate-id DTD error surfaces the conflict instead of
    hiding it.

    Returns the ``attribute_name`` value of every dropped child, in
    removal order — empty if nothing was removed — so a caller can log a
    diagnostic without re-deriving what changed.
    """
    seen: dict[str, str] = {}
    dropped: list[str] = []
    for child in list(element):
        value = child.attrib.get(attribute_name)
        if value is None:
            continue
        serialized = tostring(child, encoding="unicode")
        if value in seen:
            if seen[value] == serialized:
                element.remove(child)
                dropped.append(value)
        else:
            seen[value] = serialized
    return dropped


def rename_attribute_on_tag(element: Element, tag: str, old_name: str, new_name: str) -> int:
    """Rename ``old_name`` to ``new_name`` on every ``tag`` descendant, in place.

    A generic structural utility for "this attribute name doesn't match
    the target vocabulary, but the value is already correct" rules (e.g.
    Business Rule Book's ``data-type`` -> ``content-type`` rename on
    ``<p>``) — carries no opinion about *which* rename a business rule
    wants; that decision belongs to the calling generator. Never touches
    ``new_name`` if it's already present (never overwrites existing data).

    Returns the number of attributes actually renamed, so a caller can
    log a diagnostic without re-deriving what changed.
    """
    renamed = 0
    for descendant in element.iter(tag):
        if old_name not in descendant.attrib or new_name in descendant.attrib:
            continue
        descendant.attrib[new_name] = descendant.attrib.pop(old_name)
        renamed += 1
    return renamed


def normalize_idrefs_separator(element: Element, tag: str, attribute_name: str) -> int:
    """Replace comma(-and-whitespace) separators with a single space, in place.

    A generic structural utility for an ``IDREFS``-typed attribute whose
    value uses a comma-separated list (invalid — ``IDREFS`` is
    whitespace-separated only) where every referenced token is otherwise
    unchanged (e.g. ``"aff1, aff2"`` -> ``"aff1 aff2"``). Only rewrites
    values that actually contain a comma; never touches an already-valid
    whitespace-separated value.

    Returns the number of attribute values actually normalized.
    """
    normalized = 0
    for descendant in element.iter(tag):
        value = descendant.attrib.get(attribute_name)
        if value is None or "," not in value:
            continue
        descendant.attrib[attribute_name] = " ".join(
            token for token in re.split(r",\s*", value) if token
        )
        normalized += 1
    return normalized


def insert_after_tag(parent: Element, child: Element, after_tag: str) -> None:
    """Reposition ``child`` (already a direct child of ``parent``) to right after ``after_tag``.

    A generic structural utility for the common "this element's DTD
    content model allows any position, but our own generation order
    should still be deterministic and readable" case — e.g. Business
    Rule Book BR-164 requires a newly-generated
    ``<abbrev-journal-title abbrev-type="publisher">`` to land
    immediately after ``<journal-title>``, before any pre-existing
    ``<abbrev-journal-title>`` siblings, even though the DTD's own
    content model (a flat, order-agnostic repeatable group) would accept
    any position. If ``after_tag`` occurs more than once, inserts after
    the *last* occurrence; if it doesn't occur at all, inserts at the
    front rather than leaving ``child`` in whatever position it was
    originally appended at.
    """
    parent.remove(child)
    insert_at = 0
    for index, sibling in enumerate(parent):
        if sibling.tag == after_tag:
            insert_at = index + 1
    parent.insert(insert_at, child)


def uses_prefix(element: Element, prefix: str) -> bool:
    """Return whether any tag or attribute name in ``element``'s subtree uses ``prefix:``.

    A generic structural check for the "declare this namespace only if
    it's actually used" pattern (e.g. Business Rule Book BR-056) — never
    business-rule-specific itself.
    """
    needle = f"{prefix}:"
    for descendant in element.iter():
        if isinstance(descendant.tag, str) and descendant.tag.startswith(needle):
            return True
        if any(name.startswith(needle) for name in descendant.attrib):
            return True
    return False


def add_custom_meta_entry(
    builder: XmlDocumentBuilder, parent: Element, name: str, value: str
) -> Element:
    """Append one ``<custom-meta><meta-name>.../<meta-value>...`` entry.

    The one JATS custom-meta shape every generator that touches
    ``custom-meta-group`` needs (raw.xml's BR-042 reconstruction,
    article.xml's BR-066–071 pruning) — a structural fact, not a
    business-rule decision, so it lives here rather than being
    reimplemented per generator.
    """
    entry = builder.create_element(parent, "custom-meta")
    builder.create_element(entry, "meta-name", text=name)
    builder.create_element(entry, "meta-value", text=value)
    return entry


def strip_characters(value: str, characters: str) -> str:
    """Return ``value`` with every occurrence of any character in ``characters`` removed.

    A generic string primitive — carries no opinion about *which*
    characters an identifier format should strip (e.g. a future DOI
    formula per Business Rule Book BR-058); that decision belongs to the
    business-rule module calling this helper, never to this framework.
    """
    result = value
    for character in characters:
        result = result.replace(character, "")
    return result
