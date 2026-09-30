"""The generic Parsed Object Model.

Immutable types that closely mirror a source XML document's structure —
tag/namespace/attribute names and text content are preserved verbatim,
never renamed or normalized. This model carries **no publishing semantics
whatsoever**: it has no notion of "journal-meta," "custom-meta," "figure,"
or any other JATS/Kriyadocs/MECA-specific concept. That interpretation is
Milestone 4's job (the Metadata Extractor, building the ICAM on top of
this model) — see 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §3 for the
ICAM this model is deliberately *not*.

All types are frozen dataclasses, consistent with the ICAM's own
immutability philosophy (11_LLD_02... §3.7) applied one layer earlier,
same as the Input & Staging Layer's models (Milestone 2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class ParsedAttribute:
    """One XML attribute, with its namespace resolved.

    Attributes:
        name: The attribute's local name (namespace prefix, if any, is
            resolved separately into ``namespace_uri`` — never folded
            into this field).
        namespace_uri: The attribute's namespace URI, or ``None`` for an
            unprefixed (or default-namespace-inapplicable, per XML's own
            rule that unprefixed attributes are never in a default
            namespace) attribute.
        value: The attribute's literal string value, exactly as written
            in the source (no type coercion — see
            :mod:`meca_engine.extraction.navigation` for optional typed
            extraction helpers).
    """

    name: str
    namespace_uri: str | None
    value: str


@dataclass(frozen=True)
class ParsedElement:
    """One XML element and its subtree, mirroring the source structure exactly.

    Attributes:
        tag: The element's local name.
        namespace_uri: The element's namespace URI, or ``None`` if it has
            none.
        attributes: Every attribute on this element, in source order.
        children: Every direct child element, in source order (text-only
            content between children is not a separate node in this
            model — see ``text``/``tail``).
        text: The text immediately inside this element, before its first
            child (``None`` if there is none — this model does not
            distinguish ``<a/>`` from ``<a></a>``, matching
            ``xml.etree.ElementTree``'s own behavior).
        tail: The text immediately following this element's closing tag,
            before the next sibling (``None`` if there is none). Needed
            for faithful mixed-content representation (e.g. ``<p>a
            <b>bold</b> tail text</p>``); this model otherwise makes no
            attempt to reconstruct full mixed-content ordering beyond
            preserving this widely-used ``text``/``tail`` convention.
    """

    tag: str
    namespace_uri: str | None
    attributes: tuple[ParsedAttribute, ...] = field(default_factory=tuple)
    children: tuple[ParsedElement, ...] = field(default_factory=tuple)
    text: str | None = None
    tail: str | None = None


@dataclass(frozen=True)
class NamespaceDeclaration:
    """One ``xmlns``/``xmlns:prefix`` declaration encountered in the document.

    Attributes:
        prefix: The declared prefix, or ``None`` for a default-namespace
            (``xmlns="..."``) declaration.
        uri: The namespace URI the prefix (or default) is bound to.
    """

    prefix: str | None
    uri: str


@dataclass(frozen=True)
class DoctypeDeclaration:
    """A detected ``<!DOCTYPE ...>`` declaration — presence/shape only, not validated.

    Per the current milestone's explicit "DTD awareness (no validation
    yet)" scope: this record captures what the declaration *says*, never
    fetches or parses the referenced DTD grammar itself (that is
    ADR-025/Validation Engine scope, a later milestone).

    Attributes:
        name: The declared root element name.
        public_id: The PUBLIC identifier, if the declaration used the
            ``PUBLIC "..." "..."`` form.
        system_id: The SYSTEM identifier (from either the ``PUBLIC`` form's
            second string or a ``SYSTEM "..."`` form), if present.
        has_internal_subset: Whether the declaration includes an internal
            subset (``<!DOCTYPE name [ ... ]>``) — its contents are never
            parsed or resolved by this layer (both for scope reasons and
            because safe parsing deliberately disables internal-subset
            entity expansion; see ``xml_loader`` module docstring).
    """

    name: str
    public_id: str | None
    system_id: str | None
    has_internal_subset: bool


@dataclass(frozen=True)
class EncodingInfo:
    """What was learned about the document's encoding before/during parsing.

    Attributes:
        declared_encoding: The encoding named in the XML declaration
            (``<?xml version="1.0" encoding="..."?>``), if present and
            detectable (detection requires the prolog itself to be
            ASCII-compatible, per the XML spec's own bootstrapping rule).
        bom_encoding: The encoding implied purely by a detected byte-order
            mark, if one is present.
        effective_encoding: The encoding this layer determined was most
            likely actually used to decode the document — BOM-implied,
            else declared, else the XML spec's own default (``"utf-8"``).
            This is a best-effort determination made alongside the real
            parser, not literally introspected from it (no public API
            exposes the underlying parser's own encoding choice after
            the fact).
    """

    declared_encoding: str | None
    bom_encoding: str | None
    effective_encoding: str


@unique
class DiagnosticSeverity(str, Enum):
    """Severity of a single parse diagnostic."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@unique
class DiagnosticCategory(str, Enum):
    """What kind of thing a parse diagnostic is about.

    ``DUPLICATE_ID`` and ``MISSING_REQUIRED_VALUE`` were added in
    Milestone 4 (Metadata Extraction Layer) — an additive extension of
    this shared, generic diagnostic vocabulary (not a new mechanism), so
    both the XML Parsing Layer (Milestone 3) and the Metadata Extraction
    Layer report through the exact same ``ParseDiagnostic`` type.
    """

    ENCODING = "encoding"
    DOCTYPE = "doctype"
    NAMESPACE = "namespace"
    UNSUPPORTED_CONSTRUCT = "unsupported_construct"
    MISSING_REFERENCE = "missing_reference"
    DUPLICATE_ID = "duplicate_id"
    MISSING_REQUIRED_VALUE = "missing_required_value"


@dataclass(frozen=True)
class SourceLocation:
    """A 1-based line/column position within a source file."""

    line: int
    column: int


@dataclass(frozen=True)
class ParseDiagnostic:
    """One non-fatal observation made while loading/parsing a document.

    Diagnostics are never raised as exceptions — they are collected onto
    :attr:`ParsedDocument.diagnostics` for the caller (and, ultimately, an
    operator via structured logging) to inspect. A genuinely fatal
    condition (the document cannot be parsed at all) is reported via the
    approved exception hierarchy instead (``SourceXmlMalformedError`` /
    ``SourceUnavailableError`` — see ``xml_loader`` module docstring).

    Attributes:
        severity: How serious this observation is.
        category: What the observation is about.
        message: A human-readable description.
        location: Where in the source this was observed, when known.
    """

    severity: DiagnosticSeverity
    category: DiagnosticCategory
    message: str
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ParsedDocument:
    """The complete result of safely parsing one XML file.

    Attributes:
        source_path: The file this was parsed from.
        encoding: What was learned about the document's encoding.
        doctype: The detected ``<!DOCTYPE>`` declaration, if any.
        root: The document's root element and its full subtree.
        namespace_declarations: Every ``xmlns``/``xmlns:prefix``
            declaration encountered anywhere in the document, in the
            order first seen.
        diagnostics: Every non-fatal observation made while loading this
            document (encoding, doctype, namespace, unsupported-construct,
            and missing-reference diagnostics alike).
        raw_bytes: The exact, unmodified file bytes this document was
            parsed from. Added for the XSLT-based raw.xml generation
            path (`generators.raw_xml.xslt_transform`), which needs the
            original source XML directly rather than the parsed
            `ParsedElement` tree — every other consumer continues
            reading `root`, never this field. Defaults to ``b""`` for
            callers/fixtures that predate it.
    """

    source_path: Path
    encoding: EncodingInfo
    doctype: DoctypeDeclaration | None
    root: ParsedElement
    namespace_declarations: tuple[NamespaceDeclaration, ...] = field(default_factory=tuple)
    diagnostics: tuple[ParseDiagnostic, ...] = field(default_factory=tuple)
    raw_bytes: bytes = b""
