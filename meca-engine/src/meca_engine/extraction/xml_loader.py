"""Safe, generic XML loading — the one place raw XML bytes become a ParsedDocument.

Per the current milestone's scope: this module loads, safely parses, and
structurally reports on an XML file. It never assigns publishing meaning
to anything it finds — see :mod:`meca_engine.extraction.parsed_model`'s
module docstring for the boundary this and every sibling module in this
package respect.

**Safe parsing**: uses ``defusedxml`` rather than bare
``xml.etree.ElementTree`` — the stdlib parser does not protect against
XML entity-expansion ("billion laughs") or external-entity/DTD-fetch
attacks by default, and this milestone's "Safe XML parsing" requirement
is explicit. ``forbid_dtd`` is left ``False`` (a bare ``<!DOCTYPE>``
declaration, as every real sample document uses, is legitimate and must
still parse); ``forbid_entities``/``forbid_external`` stay at
``defusedxml``'s secure defaults (``True``), so any actual entity
declaration or external-reference resolution attempt is rejected.
"""

from __future__ import annotations

import re
from io import BytesIO
from typing import TYPE_CHECKING, cast
from xml.etree.ElementTree import Element, ParseError
from xml.parsers.expat import ExpatError

import defusedxml.ElementTree as DefusedET
from defusedxml.common import DefusedXmlException

from meca_engine.exceptions import SourceUnavailableError, SourceXmlMalformedError
from meca_engine.extraction.diagnostics import find_dangling_references
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
)

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.logging_ import StructuredLogger

_STAGE = "meca_engine.extraction.xml_loader"

_DEFAULT_ENCODING = "utf-8"

# BOM signatures, longest/most-specific first (UTF-32 LE's BOM is a
# superset-prefix of UTF-16 LE's, so order matters).
_BOM_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\x00\x00\xfe\xff", "utf-32-be"),
    (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xfe\xff", "utf-16-be"),
    (b"\xff\xfe", "utf-16-le"),
)

_XML_DECLARATION_PATTERN = re.compile(
    rb"""^\s*<\?xml\s+version\s*=\s*["'][^"']+["']\s+encoding\s*=\s*["']([^"']+)["']""",
)

_DOCTYPE_PATTERN = re.compile(
    r"<!DOCTYPE\s+(?P<name>[A-Za-z_][\w:.-]*)"
    r"(?:\s+PUBLIC\s+(?P<pubquote>['\"])(?P<public_id>.*?)(?P=pubquote)"
    r"\s+(?P<sysquote1>['\"])(?P<system_id1>.*?)(?P=sysquote1)"
    r"|\s+SYSTEM\s+(?P<sysquote2>['\"])(?P<system_id2>.*?)(?P=sysquote2)"
    r")?"
    r"\s*(?P<internal>\[)?",
    re.DOTALL,
)


class XmlLoader:
    """Loads an XML file from disk into a :class:`ParsedDocument`.

    Attributes:
        reference_attribute_names: Which unprefixed attribute names are
            treated as internal cross-references when checking for
            dangling references (see
            :mod:`meca_engine.extraction.diagnostics`). Configurable so
            this loader stays usable for any XML dialect, not just the
            ones the current sample documents happen to use.
    """

    def __init__(
        self,
        logger: StructuredLogger,
        *,
        reference_attribute_names: tuple[str, ...] = ("rid",),
    ) -> None:
        """Initialize the loader.

        Args:
            logger: The structured logger to emit loading events through.
            reference_attribute_names: Forwarded to
                :func:`~meca_engine.extraction.diagnostics.find_dangling_references`.
        """
        self._logger = logger
        self._reference_attribute_names = reference_attribute_names

    def load(self, path: Path) -> ParsedDocument:
        """Load and safely parse one XML file.

        Args:
            path: The file to load.

        Returns:
            The fully-populated :class:`ParsedDocument`.

        Raises:
            SourceUnavailableError: If ``path`` does not exist or cannot
                be read.
            SourceXmlMalformedError: If the file's content is not
                well-formed XML, or safe parsing rejected an entity/
                external-reference construct.
        """
        raw_bytes = self._read_file(path)

        bom_encoding = self._detect_bom(raw_bytes)
        bytes_after_bom = raw_bytes[self._bom_length(raw_bytes) :]
        declared_encoding = self._detect_declared_encoding(bytes_after_bom)
        effective_encoding = bom_encoding or declared_encoding or _DEFAULT_ENCODING
        encoding_info = EncodingInfo(
            declared_encoding=declared_encoding,
            bom_encoding=bom_encoding,
            effective_encoding=effective_encoding,
        )

        diagnostics: list[ParseDiagnostic] = []
        diagnostics.extend(self._encoding_diagnostics(bom_encoding, declared_encoding))

        prolog_text = raw_bytes.decode(effective_encoding, errors="replace")
        doctype, doctype_diagnostics = self._detect_doctype(prolog_text)
        diagnostics.extend(doctype_diagnostics)

        namespace_declarations = self._collect_namespaces(raw_bytes, path)
        root_element = self._parse_tree(raw_bytes, path)
        parsed_root = self._convert_element(root_element)

        diagnostics.extend(
            find_dangling_references(
                parsed_root, reference_attribute_names=self._reference_attribute_names
            )
        )

        document = ParsedDocument(
            source_path=path,
            encoding=encoding_info,
            doctype=doctype,
            root=parsed_root,
            namespace_declarations=namespace_declarations,
            diagnostics=tuple(diagnostics),
            raw_bytes=raw_bytes,
        )

        self._logger.info(
            "XML document parsed successfully",
            stage=_STAGE,
            context={
                "source_path": str(path),
                "root_tag": parsed_root.tag,
                "effective_encoding": effective_encoding,
                "diagnostic_count": len(document.diagnostics),
            },
        )
        return document

    # --- loading & safe parsing ---

    def _read_file(self, path: Path) -> bytes:
        try:
            return path.read_bytes()
        except OSError as exc:
            raise SourceUnavailableError(
                f"Could not read XML file: {path}",
                stage=_STAGE,
                inner_cause=exc,
            ) from exc

    def _parse_tree(self, raw_bytes: bytes, path: Path) -> Element:
        try:
            tree = DefusedET.parse(BytesIO(raw_bytes))
            root = tree.getroot()
            if root is None:  # pragma: no cover
                # Not reachable via any known well-formed-XML input (a
                # successfully-parsed ElementTree always has a root) — this
                # branch exists purely so the return type stays accurate,
                # matching Milestone 2's established precedent (see
                # Boto3S3Client) for defensive code no realistic test can
                # trigger through the public API.
                raise SourceXmlMalformedError(
                    f"XML file parsed but produced no root element: {path}",
                    stage=_STAGE,
                    rule_id="BR-001",
                )
            return root
        except (ParseError, ExpatError) as exc:
            location = self._format_error_location(exc)
            raise SourceXmlMalformedError(
                f"XML file is not well-formed: {path}{location}: {exc}",
                stage=_STAGE,
                rule_id="BR-001",
                inner_cause=exc,
            ) from exc
        except DefusedXmlException as exc:
            raise SourceXmlMalformedError(
                f"XML file rejected by safe-parsing checks (entity/external-reference "
                f"construct forbidden): {path}: {exc}",
                stage=_STAGE,
                inner_cause=exc,
            ) from exc

    def _collect_namespaces(self, raw_bytes: bytes, path: Path) -> tuple[NamespaceDeclaration, ...]:
        declarations: list[NamespaceDeclaration] = []
        seen: set[tuple[str | None, str]] = set()
        try:
            for _event, value in DefusedET.iterparse(BytesIO(raw_bytes), events=("start-ns",)):
                # The installed type stubs describe iterparse's (event, value)
                # pair generically across every possible event kind (typed as
                # if `value` were always an Element); for a "start-ns" event
                # specifically, the real runtime value is always a
                # (prefix, uri) string pair — hence the explicit cast.
                prefix, uri = cast("tuple[str | None, str]", value)
                key = (prefix or None, uri)
                if key not in seen:
                    seen.add(key)
                    declarations.append(NamespaceDeclaration(prefix=prefix or None, uri=uri))
        except (ParseError, ExpatError, DefusedXmlException):
            # Already reported by _parse_tree's own attempt; avoid double-raising
            # from this secondary pass over the same bytes.
            return ()
        return tuple(declarations)

    @staticmethod
    def _format_error_location(exc: Exception) -> str:
        # xml.etree.ElementTree.ParseError exposes `.position` (line, column);
        # a raw xml.parsers.expat.ExpatError exposes `.lineno`/`.offset`
        # instead — both are handled since either could reach this point.
        position = getattr(exc, "position", None)
        if position is not None:
            line, column = position
            return f" (line {line}, column {column})"
        lineno = getattr(exc, "lineno", None)
        offset = getattr(exc, "offset", None)
        if lineno is None:
            return ""
        if offset is None:
            return f" (line {lineno})"
        return f" (line {lineno}, column {offset})"

    # --- encoding detection ---

    @staticmethod
    def _detect_bom(raw_bytes: bytes) -> str | None:
        for signature, encoding in _BOM_SIGNATURES:
            if raw_bytes.startswith(signature):
                return encoding
        return None

    @staticmethod
    def _bom_length(raw_bytes: bytes) -> int:
        for signature, _encoding in _BOM_SIGNATURES:
            if raw_bytes.startswith(signature):
                return len(signature)
        return 0

    @staticmethod
    def _detect_declared_encoding(raw_bytes: bytes) -> str | None:
        # Expects any byte-order mark to already be stripped from the
        # front of ``raw_bytes`` (see the ``load()`` call site) — the XML
        # declaration's ``<?xml`` must be the very first thing the regex
        # sees, per the XML spec's own bootstrapping rule.
        match = _XML_DECLARATION_PATTERN.match(raw_bytes)
        if match is None:
            return None
        return match.group(1).decode("ascii", errors="replace")

    @staticmethod
    def _encoding_diagnostics(
        bom_encoding: str | None, declared_encoding: str | None
    ) -> tuple[ParseDiagnostic, ...]:
        diagnostics: list[ParseDiagnostic] = []
        if bom_encoding is None and declared_encoding is None:
            diagnostics.append(
                ParseDiagnostic(
                    severity=DiagnosticSeverity.INFO,
                    category=DiagnosticCategory.ENCODING,
                    message=(
                        "No byte-order mark and no XML declaration encoding found; "
                        f"assuming the XML specification default ({_DEFAULT_ENCODING})"
                    ),
                )
            )
        elif bom_encoding is not None and declared_encoding is not None:
            bom_family = bom_encoding.replace("-sig", "").replace("-", "").lower()
            declared_family = declared_encoding.replace("-", "").lower()
            if bom_family not in declared_family and declared_family not in bom_family:
                diagnostics.append(
                    ParseDiagnostic(
                        severity=DiagnosticSeverity.WARNING,
                        category=DiagnosticCategory.ENCODING,
                        message=(
                            f"Byte-order mark implies {bom_encoding!r} but the XML "
                            f"declaration says encoding={declared_encoding!r}; "
                            f"preferring the byte-order mark"
                        ),
                    )
                )
        return tuple(diagnostics)

    # --- DOCTYPE detection (presence/shape only — never validated) ---

    @staticmethod
    def _detect_doctype(text: str) -> tuple[DoctypeDeclaration | None, tuple[ParseDiagnostic, ...]]:
        match = _DOCTYPE_PATTERN.search(text)
        if match is None:
            return None, ()

        system_id = match.group("system_id1") or match.group("system_id2")
        doctype = DoctypeDeclaration(
            name=match.group("name"),
            public_id=match.group("public_id"),
            system_id=system_id,
            has_internal_subset=match.group("internal") is not None,
        )
        diagnostics: list[ParseDiagnostic] = []
        if doctype.has_internal_subset:
            diagnostics.append(
                ParseDiagnostic(
                    severity=DiagnosticSeverity.WARNING,
                    category=DiagnosticCategory.UNSUPPORTED_CONSTRUCT,
                    message=(
                        "DOCTYPE declares an internal subset; its contents are not "
                        "parsed or resolved by this layer (entity declarations "
                        "within it are inert under safe parsing)"
                    ),
                )
            )
        return doctype, tuple(diagnostics)

    # --- tree conversion ---

    @classmethod
    def _convert_element(cls, element: Element) -> ParsedElement:
        namespace_uri, local_tag = cls._split_clark(element.tag)
        attributes = tuple(
            ParsedAttribute(
                name=cls._split_clark(name)[1],
                namespace_uri=cls._split_clark(name)[0],
                value=value,
            )
            for name, value in element.attrib.items()
        )
        children = tuple(cls._convert_element(child) for child in element)
        return ParsedElement(
            tag=local_tag,
            namespace_uri=namespace_uri,
            attributes=attributes,
            children=children,
            text=element.text,
            tail=element.tail,
        )

    @staticmethod
    def _split_clark(qualified_name: str) -> tuple[str | None, str]:
        if qualified_name.startswith("{"):
            uri, _, local = qualified_name[1:].partition("}")
            return uri, local
        return None, qualified_name
