"""Generic discovery of structural file/resource references within a document.

Finds every element carrying a recognized *structural* reference
attribute (XLink's ``xlink:href``, or the plain ``href``/``src``
conventions) — covering the shapes a real document uses for images,
supplementary files, and related external resources alike — without ever
deciding *what kind* of thing is being referenced. Recognizing
``xlink:href`` is XLink/W3C-standard structural awareness, not a
publishing-domain judgment call: this module never inspects the
referencing element's own tag name to decide "this is an image" or "this
is supplementary material" — that categorization is Business Rule Book
territory (BR-078 etc.), driven by source-system metadata that doesn't
exist at this layer, and is Milestone 4+'s job.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from meca_engine.extraction.navigation import iter_descendants

if TYPE_CHECKING:
    from meca_engine.extraction.parsed_model import ParsedDocument

XLINK_NAMESPACE_URI = "http://www.w3.org/1999/xlink"

#: (namespace_uri, attribute_name) pairs recognized as structural
#: references to an external resource. Order is not significant.
DEFAULT_REFERENCE_ATTRIBUTES: tuple[tuple[str | None, str], ...] = (
    (XLINK_NAMESPACE_URI, "href"),
    (None, "href"),
    (None, "src"),
)


@dataclass(frozen=True)
class FileReference:
    """One structural reference from an element to an external resource.

    Attributes:
        referencing_tag: The local tag name of the element carrying the
            reference attribute.
        referencing_namespace_uri: That element's namespace URI, if any.
        attribute_name: The reference attribute's local name (``"href"``
            or ``"src"``).
        attribute_namespace_uri: The reference attribute's namespace URI
            (e.g. the XLink namespace for ``xlink:href``), or ``None``
            for an unprefixed ``href``/``src``.
        value: The raw reference value, exactly as written (a relative
            path, a filename, or a full URI — this module makes no
            attempt to resolve or classify it).
    """

    referencing_tag: str
    referencing_namespace_uri: str | None
    attribute_name: str
    attribute_namespace_uri: str | None
    value: str


def discover_file_references(
    document: ParsedDocument,
    *,
    reference_attributes: tuple[tuple[str | None, str], ...] = DEFAULT_REFERENCE_ATTRIBUTES,
) -> tuple[FileReference, ...]:
    """Find every structural reference to an external resource in a document.

    Args:
        document: The parsed document to scan.
        reference_attributes: Which (namespace_uri, attribute_name) pairs
            count as a reference. Defaults to XLink's ``href``, plain
            ``href``, and plain ``src`` — the conventions covering
            images, supplementary-material links, and related-resource
            links alike in practice.

    Returns:
        One :class:`FileReference` per matching attribute found, in
        document order.
    """
    results: list[FileReference] = []
    for element in iter_descendants(document.root):
        for attribute in element.attributes:
            for namespace_uri, name in reference_attributes:
                if attribute.name == name and attribute.namespace_uri == namespace_uri:
                    results.append(
                        FileReference(
                            referencing_tag=element.tag,
                            referencing_namespace_uri=element.namespace_uri,
                            attribute_name=attribute.name,
                            attribute_namespace_uri=attribute.namespace_uri,
                            value=attribute.value,
                        )
                    )
    return tuple(results)
