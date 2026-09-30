"""Reusable, generic navigation helpers over the Parsed Object Model.

Every function here is a pure function operating on
:class:`~meca_engine.extraction.parsed_model.ParsedElement` /
:class:`~meca_engine.extraction.parsed_model.ParsedDocument` — none of them
know anything about JATS, Kriyadocs, or MECA. A future milestone's
business-rule-driven extraction code is expected to be built *using*
these helpers, never by re-implementing tree-walking logic itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from meca_engine.extraction.parsed_model import ParsedElement

_DEFAULT_ID_ATTRIBUTE_NAMES: tuple[str, ...] = ("id",)
XML_NAMESPACE_URI = "http://www.w3.org/XML/1998/namespace"


def iter_descendants(
    element: ParsedElement, *, include_self: bool = True
) -> Iterator[ParsedElement]:
    """Iterate every element in a subtree, depth-first, in document order.

    Args:
        element: The subtree root to iterate from.
        include_self: Whether to yield ``element`` itself first.

    Yields:
        Each element in the subtree, ``element`` included unless
        ``include_self`` is ``False``.
    """
    if include_self:
        yield element
    for child in element.children:
        yield from iter_descendants(child, include_self=True)


def find_first(
    element: ParsedElement,
    tag: str,
    *,
    namespace_uri: str | None = None,
    recursive: bool = True,
) -> ParsedElement | None:
    """Find the first matching descendant (or direct child) element.

    Args:
        element: The element to search within (not itself matched).
        tag: The local tag name to match.
        namespace_uri: If given, also require this exact namespace URI
            (``None`` matches only elements with no namespace).
        recursive: If ``True`` (default), search the whole subtree; if
            ``False``, only search direct children.

    Returns:
        The first matching element in document order, or ``None`` if
        there isn't one.
    """
    candidates = (
        iter_descendants(element, include_self=False) if recursive else iter(element.children)
    )
    for candidate in candidates:
        if candidate.tag == tag and candidate.namespace_uri == namespace_uri:
            return candidate
    return None


def find_all(
    element: ParsedElement,
    tag: str,
    *,
    namespace_uri: str | None = None,
    recursive: bool = True,
) -> tuple[ParsedElement, ...]:
    """Find every matching descendant (or direct child) element.

    Args:
        element: The element to search within (not itself matched).
        tag: The local tag name to match.
        namespace_uri: If given, also require this exact namespace URI.
        recursive: If ``True`` (default), search the whole subtree; if
            ``False``, only search direct children.

    Returns:
        Every matching element, in document order.
    """
    candidates = (
        iter_descendants(element, include_self=False) if recursive else iter(element.children)
    )
    return tuple(
        candidate
        for candidate in candidates
        if candidate.tag == tag and candidate.namespace_uri == namespace_uri
    )


def find_by_path(root: ParsedElement, path: str) -> ParsedElement | None:
    """Navigate a simple, slash-separated path of direct-child tag names.

    This is a deliberately simplified stand-in for full XPath — it
    supports only ``"tag/tag/tag"``-style direct-descendant paths (no
    predicates, no namespace prefixes, no attribute axes). Provided
    because the current task calls for "XPath helpers where appropriate";
    a full XPath engine was judged out of scope/unnecessary for a layer
    that must not interpret document semantics.

    Args:
        root: The element the path is relative to.
        path: A ``/``-separated sequence of local tag names, each
            resolved as a direct child of the previous step.

    Returns:
        The element at the end of the path, or ``None`` if any step
        doesn't match.
    """
    current = root
    for segment in path.split("/"):
        if not segment:
            continue
        match = find_first(current, segment, recursive=False)
        if match is None:
            return None
        current = match
    return current


def get_attribute(
    element: ParsedElement, name: str, *, namespace_uri: str | None = None
) -> str | None:
    """Safely look up one attribute's value.

    Args:
        element: The element to look on.
        name: The attribute's local name.
        namespace_uri: The attribute's namespace URI, or ``None`` for an
            unprefixed attribute (the common case).

    Returns:
        The attribute's value, or ``None`` if it isn't present — never
        raises for a missing attribute.
    """
    for attribute in element.attributes:
        if attribute.name == name and attribute.namespace_uri == namespace_uri:
            return attribute.value
    return None


def get_text(element: ParsedElement, *, recursive: bool = False) -> str:
    """Return an element's text content.

    Args:
        element: The element to read text from.
        recursive: If ``False`` (default), return only ``element.text``
            (the text immediately inside, before any child) — never
            ``None``, an absent text node becomes ``""``. If ``True``,
            concatenate the text of every descendant too (each child's
            ``text`` followed by its ``tail``, recursively), giving a
            simple flattened "all the text in this subtree" view.

    Returns:
        The requested text, never ``None``.
    """
    if not recursive:
        return element.text or ""
    parts = [element.text or ""]
    for child in element.children:
        parts.append(get_text(child, recursive=True))
        parts.append(child.tail or "")
    return "".join(parts)


def as_int(value: str | None) -> int | None:
    """Safely convert an optional string to an int.

    Args:
        value: The string to convert, or ``None``.

    Returns:
        The parsed integer, or ``None`` if ``value`` is ``None`` or not a
        valid integer literal (never raises).
    """
    if value is None:
        return None
    try:
        return int(value.strip())
    except ValueError:
        return None


def as_float(value: str | None) -> float | None:
    """Safely convert an optional string to a float.

    Args:
        value: The string to convert, or ``None``.

    Returns:
        The parsed float, or ``None`` if ``value`` is ``None`` or not a
        valid float literal (never raises).
    """
    if value is None:
        return None
    try:
        return float(value.strip())
    except ValueError:
        return None


_TRUE_LITERALS = frozenset({"true", "1", "yes"})
_FALSE_LITERALS = frozenset({"false", "0", "no"})


def as_bool(value: str | None) -> bool | None:
    """Safely convert an optional string to a bool.

    Recognizes the common XML boolean literals (``true``/``false``,
    ``1``/``0``, ``yes``/``no``), case-insensitively.

    Args:
        value: The string to convert, or ``None``.

    Returns:
        The parsed boolean, or ``None`` if ``value`` is ``None`` or not
        one of the recognized literals (never raises).
    """
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in _TRUE_LITERALS:
        return True
    if normalized in _FALSE_LITERALS:
        return False
    return None


def build_id_index(
    root: ParsedElement, *, id_attribute_names: tuple[str, ...] = _DEFAULT_ID_ATTRIBUTE_NAMES
) -> Mapping[str, ParsedElement]:
    """Build a lookup of every element carrying one of the given id-like attributes.

    Args:
        root: The subtree to index.
        id_attribute_names: Which unprefixed attribute names count as an
            "id" for this index. Defaults to ``("id",)``, the near-universal
            convention; ``xml:id`` (the XML-namespace-qualified form) is
            always additionally recognized.

    Returns:
        A mapping from id value to the (first) element carrying it. If
        more than one element shares an id value, only the first
        encountered (in document order) is retained — this index does
        not itself flag that as an error; a caller wanting that check
        should compare ``len(index)`` against a separate full count.
    """
    index: dict[str, ParsedElement] = {}
    for element in iter_descendants(root):
        for attribute in element.attributes:
            is_plain_id = attribute.namespace_uri is None and attribute.name in id_attribute_names
            is_xml_id = attribute.namespace_uri == XML_NAMESPACE_URI and attribute.name == "id"
            if (is_plain_id or is_xml_id) and attribute.value not in index:
                index[attribute.value] = element
    return index
