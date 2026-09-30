"""XML Document Builder — Generator Framework (Milestone 6A).

A reusable, business-logic-free XML tree builder and serializer, built on
:mod:`xml.etree.ElementTree` for tree construction and escaping, with a
hand-written declaration/DOCTYPE prologue so every structural choice
(encoding, standalone, DOCTYPE presence) is explicit rather than
ElementTree's own defaulting rules.

Deliberately avoids ElementTree's ``{namespace-uri}tag`` clark-notation
tags and :func:`xml.etree.ElementTree.register_namespace` entirely — see
:mod:`meca_engine.generators.xml.namespaces` for why. Every tag/attribute
name passed to this module is already the final literal string a
generator wants written (e.g. ``"xlink:href"``), never a namespace URI to
resolve.

Deterministic ordering is a property of *how this module is used*, not
something it enforces by sorting: attributes are written in the exact
``dict`` iteration order the caller supplies, and children in the exact
order they were appended — callers must build with an explicit, stable
order (never iterate an unordered set/dict) for the output to be
deterministic. This module never reorders anything itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from xml.etree.ElementTree import (
    Comment,
    Element,
    ProcessingInstruction,
    SubElement,
    indent,
    tostring,
)
from xml.sax.saxutils import unescape

from meca_engine.exceptions import XmlSerializationError

if TYPE_CHECKING:
    from collections.abc import Mapping

_STAGE = "generators.xml.builder"

_CDATA_START = "\x00__MECA_CDATA_START__\x00"
_CDATA_END = "\x00__MECA_CDATA_END__\x00"
_CDATA_PATTERN = re.compile(re.escape(_CDATA_START) + r"(.*?)" + re.escape(_CDATA_END), re.DOTALL)


class CData(str):
    """A text value that must be serialized as ``<![CDATA[...]]>``, not escaped.

    Assign an instance of this to an element's text (via
    :meth:`XmlDocumentBuilder.create_element`'s ``text`` argument) to
    request CDATA rendering. Plain ``str`` text is always escaped
    normally — this is an explicit opt-in, never inferred from content.
    """


@dataclass(frozen=True)
class DoctypeDeclaration:
    """A DOCTYPE declaration to prepend before the root element.

    Attributes:
        root_tag: The document's root element name (must match the
            actual root element's tag).
        public_id: The DTD's public identifier, if any (e.g.
            ``"-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.3 20210610//EN"``).
        system_id: The DTD's system identifier (a URL or relative path).
    """

    root_tag: str
    public_id: str | None = None
    system_id: str | None = None

    def render(self) -> str:
        """Render this declaration's exact DOCTYPE line."""
        if self.public_id is not None and self.system_id is not None:
            return f'<!DOCTYPE {self.root_tag} PUBLIC "{self.public_id}" "{self.system_id}">'
        if self.system_id is not None:
            return f'<!DOCTYPE {self.root_tag} SYSTEM "{self.system_id}">'
        return f"<!DOCTYPE {self.root_tag}>"


class XmlDocumentBuilder:
    """Builds and serializes one XML document tree.

    Stateless beyond the tree it is handed — a single instance may be
    reused across many documents/articles (no per-instance mutable
    configuration; every method takes what it needs as arguments).
    """

    def create_root(self, tag: str, *, attributes: Mapping[str, str] | None = None) -> Element:
        """Create a new root element.

        Args:
            tag: The root element's tag name (may include a literal
                prefix, e.g. ``"article"``).
            attributes: Attributes to set, in the exact order they
                should be serialized (e.g. namespace declarations from
                :meth:`~meca_engine.generators.xml.namespaces.NamespaceManager.declarations`
                followed by content attributes).

        Returns:
            The new, childless root element.
        """
        return Element(tag, dict(attributes) if attributes is not None else {})

    def create_element(
        self,
        parent: Element,
        tag: str,
        *,
        attributes: Mapping[str, str] | None = None,
        text: str | None = None,
    ) -> Element:
        """Append a new child element to ``parent``.

        Args:
            parent: The element to append to.
            tag: The new element's tag name.
            attributes: Attributes to set, in serialization order.
            text: The element's text content, if any. Pass a
                :class:`CData` instance instead of ``str`` to request
                CDATA rendering.

        Returns:
            The newly created, appended element.
        """
        element = SubElement(parent, tag, dict(attributes) if attributes is not None else {})
        if text is not None:
            element.text = f"{_CDATA_START}{text}{_CDATA_END}" if isinstance(text, CData) else text
        return element

    def import_subtree(self, element: Element) -> Element:
        """Deep-copy ``element`` (and its whole subtree) for attachment elsewhere.

        Use this to bring a subtree from a *different* tree (e.g. one
        generator importing another generator's already-built output —
        see :class:`~meca_engine.generators.raw_xml.generator.RawXmlGenerator`/
        :class:`~meca_engine.generators.article_xml.generator.ArticleXmlGenerator`)
        into this builder's tree without aliasing the original — mutating
        the copy (e.g. stripping attributes) never affects the source.
        """
        return _clone(element)

    def add_comment(self, parent: Element, text: str) -> Element[Any]:
        """Append an XML comment (``<!-- text -->``) as a child of ``parent``."""
        comment = Comment(f" {text} ")
        parent.append(comment)
        return comment

    def add_processing_instruction(
        self, parent: Element, target: str, text: str = ""
    ) -> Element[Any]:
        """Append a processing instruction (``<?target text?>``) as a child of ``parent``."""
        pi = ProcessingInstruction(target, text)
        parent.append(pi)
        return pi

    def serialize(
        self,
        root: Element,
        *,
        pretty: bool = True,
        encoding: str | None = "UTF-8",
        xml_declaration: bool = True,
        standalone: bool | None = None,
        doctype: DoctypeDeclaration | None = None,
        indent_spaces: int = 2,
    ) -> bytes:
        """Serialize a tree to its final XML bytes.

        Args:
            root: The document's root element.
            pretty: If ``True`` (default), indent the tree before
                serializing (compact mode: pass ``False``).
            encoding: The declared/actual output encoding. Pass ``None``
                to omit the ``encoding`` attribute from the declaration
                entirely (a document with no declared encoding still
                defaults to UTF-8 bytes).
            xml_declaration: Whether to emit an ``<?xml ...?>`` prologue
                line at all.
            standalone: If not ``None``, adds a ``standalone="yes"``/
                ``"no"`` attribute to the declaration.
            doctype: An optional DOCTYPE declaration to emit after the
                XML declaration and before the root element.
            indent_spaces: Indentation width used when ``pretty=True``.

        Returns:
            The complete document as bytes, in ``encoding`` (or UTF-8 if
            ``encoding`` is ``None``).

        Raises:
            XmlSerializationError: If the tree cannot be serialized in
                the requested encoding.
        """
        working_root = _clone(root)
        if pretty:
            indent(working_root, space=" " * indent_spaces)

        try:
            body = tostring(working_root, encoding="unicode")
        except (ValueError, TypeError) as exc:
            raise XmlSerializationError(
                "Failed to serialize XML tree", stage=_STAGE, inner_cause=exc
            ) from exc

        body = _CDATA_PATTERN.sub(lambda match: f"<![CDATA[{unescape(match.group(1))}]]>", body)

        lines: list[str] = []
        if xml_declaration:
            lines.append(_render_declaration(encoding=encoding, standalone=standalone))
        if doctype is not None:
            lines.append(doctype.render())
        lines.append(body)
        text = "\n".join(lines)
        if pretty and not text.endswith("\n"):
            text += "\n"

        effective_encoding = encoding or "utf-8"
        try:
            return text.encode(effective_encoding)
        except LookupError as exc:
            raise XmlSerializationError(
                f"Unknown output encoding: {effective_encoding!r}", stage=_STAGE, inner_cause=exc
            ) from exc


def _render_declaration(*, encoding: str | None, standalone: bool | None) -> str:
    parts = ['version="1.0"']
    if encoding is not None:
        parts.append(f'encoding="{encoding}"')
    if standalone is not None:
        parts.append(f'standalone="{"yes" if standalone else "no"}"')
    return f"<?xml {' '.join(parts)}?>"


def _clone(element: Element) -> Element:
    clone = Element(element.tag, dict(element.attrib))
    clone.text = element.text
    clone.tail = element.tail
    for child in element:
        clone.append(_clone(child))
    return clone
