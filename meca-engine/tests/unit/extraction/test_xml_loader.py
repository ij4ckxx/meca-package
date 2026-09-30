"""Unit tests for meca_engine.extraction.xml_loader.XmlLoader."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from meca_engine.exceptions import SourceUnavailableError, SourceXmlMalformedError
from meca_engine.extraction.navigation import get_attribute
from meca_engine.extraction.parsed_model import DiagnosticCategory, DiagnosticSeverity
from meca_engine.extraction.xml_loader import XmlLoader
from meca_engine.logging_ import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

pytestmark = pytest.mark.unit


@pytest.fixture
def loader() -> XmlLoader:
    return XmlLoader(get_logger("test.xml_loader"))


# --- valid XML ---


def test_loads_a_simple_valid_document(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    path = write_xml(b'<?xml version="1.0" encoding="UTF-8"?>\n<root><child>hi</child></root>')

    document = loader.load(path)

    assert document.root.tag == "root"
    assert document.root.children[0].tag == "child"
    assert document.root.children[0].text == "hi"
    assert document.source_path == path


def test_loads_document_with_no_xml_declaration(
    loader: XmlLoader, write_xml: Callable[..., Path]
) -> None:
    path = write_xml(b"<root/>")

    document = loader.load(path)

    assert document.root.tag == "root"
    assert document.encoding.declared_encoding is None
    assert document.encoding.effective_encoding == "utf-8"
    info_diagnostics = [
        d for d in document.diagnostics if d.category is DiagnosticCategory.ENCODING
    ]
    assert any(d.severity is DiagnosticSeverity.INFO for d in info_diagnostics)


# --- invalid / broken XML ---


def test_raises_for_malformed_xml(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    path = write_xml(b"<root><unclosed></root>")

    with pytest.raises(SourceXmlMalformedError) as excinfo:
        loader.load(path)

    assert "line" in excinfo.value.message


def test_raises_for_empty_file(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    path = write_xml(b"")

    with pytest.raises(SourceXmlMalformedError):
        loader.load(path)


def test_raises_for_truncated_xml(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    path = write_xml(b"<root><child>incomplete")

    with pytest.raises(SourceXmlMalformedError):
        loader.load(path)


def test_malformed_error_has_br001_rule_id(
    loader: XmlLoader, write_xml: Callable[..., Path]
) -> None:
    path = write_xml(b"<root><bad></root>")

    with pytest.raises(SourceXmlMalformedError) as excinfo:
        loader.load(path)

    assert excinfo.value.rule_id == "BR-001"


# --- missing file ---


def test_raises_source_unavailable_for_missing_file(loader: XmlLoader, tmp_path: Path) -> None:
    with pytest.raises(SourceUnavailableError):
        loader.load(tmp_path / "does-not-exist.xml")


def test_raises_source_unavailable_for_a_directory(loader: XmlLoader, tmp_path: Path) -> None:
    directory = tmp_path / "a-directory"
    directory.mkdir()

    with pytest.raises(SourceUnavailableError):
        loader.load(directory)


# --- unsafe XML (XXE / entity expansion) ---


def test_rejects_internal_entity_declaration(
    loader: XmlLoader, write_xml: Callable[..., Path]
) -> None:
    path = write_xml(
        b'<?xml version="1.0"?>\n<!DOCTYPE root [\n<!ENTITY xxe "test">\n]>\n<root>&xxe;</root>'
    )

    with pytest.raises(SourceXmlMalformedError, match="forbidden"):
        loader.load(path)


# --- namespace handling ---


def test_captures_namespace_declarations(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    path = write_xml(
        b'<root xmlns:xlink="http://www.w3.org/1999/xlink" xmlns="urn:default"><xlink:ref/></root>'
    )

    document = loader.load(path)

    uris_and_prefixes = {(d.prefix, d.uri) for d in document.namespace_declarations}
    assert ("xlink", "http://www.w3.org/1999/xlink") in uris_and_prefixes
    assert (None, "urn:default") in uris_and_prefixes


def test_element_namespace_uri_resolved(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    path = write_xml(b'<root xmlns:x="urn:x"><x:child/></root>')

    document = loader.load(path)

    child = document.root.children[0]
    assert child.tag == "child"
    assert child.namespace_uri == "urn:x"


def test_namespaced_attribute_resolved(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    path = write_xml(
        b'<root xmlns:xlink="http://www.w3.org/1999/xlink"><graphic xlink:href="fig1.jpg"/></root>'
    )

    document = loader.load(path)

    graphic = document.root.children[0]
    value = get_attribute(graphic, "href", namespace_uri="http://www.w3.org/1999/xlink")
    assert value == "fig1.jpg"


def test_no_namespaces_produces_empty_tuple(
    loader: XmlLoader, write_xml: Callable[..., Path]
) -> None:
    path = write_xml(b"<root><child/></root>")

    document = loader.load(path)

    assert document.namespace_declarations == ()


def test_duplicate_namespace_declaration_deduplicated(
    loader: XmlLoader, write_xml: Callable[..., Path]
) -> None:
    # The same prefix/URI pair re-declared on a nested element must only
    # appear once in namespace_declarations.
    path = write_xml(b'<root xmlns:x="urn:x"><child xmlns:x="urn:x"><x:leaf/></child></root>')

    document = loader.load(path)

    matching = [d for d in document.namespace_declarations if d.prefix == "x" and d.uri == "urn:x"]
    assert len(matching) == 1


# --- encoding variations ---


def test_utf8_bom_detected(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    path = write_xml(b'\xef\xbb\xbf<?xml version="1.0" encoding="UTF-8"?>\n<root/>')

    document = loader.load(path)

    assert document.encoding.bom_encoding == "utf-8-sig"
    assert document.root.tag == "root"


def test_utf16_bom_detected_and_parses(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    content = '<?xml version="1.0" encoding="UTF-16"?>\n<root>text</root>'.encode("utf-16")
    path = write_xml(content)

    document = loader.load(path)

    assert document.encoding.bom_encoding in {"utf-16-le", "utf-16-be"}
    assert document.root.text == "text"


def test_declared_encoding_without_bom(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    path = write_xml(b'<?xml version="1.0" encoding="ISO-8859-1"?>\n<root/>')

    document = loader.load(path)

    assert document.encoding.declared_encoding == "ISO-8859-1"
    assert document.encoding.bom_encoding is None


def test_bom_declared_encoding_conflict_produces_warning(
    loader: XmlLoader, write_xml: Callable[..., Path]
) -> None:
    # BOM says UTF-8, declaration claims ISO-8859-1 — a genuine mismatch
    # that the underlying parser still tolerates (unlike a UTF-16-family
    # mismatch, which the parser itself rejects outright before this
    # layer's own diagnostic logic would ever run).
    path = write_xml(b'\xef\xbb\xbf<?xml version="1.0" encoding="ISO-8859-1"?>\n<root/>')

    document = loader.load(path)

    encoding_warnings = [
        d
        for d in document.diagnostics
        if d.category is DiagnosticCategory.ENCODING and d.severity is DiagnosticSeverity.WARNING
    ]
    assert len(encoding_warnings) == 1


def test_incompatible_utf16_declaration_with_utf8_bom_is_rejected_by_the_parser(
    loader: XmlLoader, write_xml: Callable[..., Path]
) -> None:
    # A UTF-8 BOM combined with an "encoding=UTF-16" declaration is
    # invalid at the parser level (not just a soft mismatch this layer
    # can warn about) — verifies this reaches the caller as the approved
    # SourceXmlMalformedError, not an unhandled parser exception.
    path = write_xml(b'\xef\xbb\xbf<?xml version="1.0" encoding="UTF-16"?>\n<root/>')

    with pytest.raises(SourceXmlMalformedError):
        loader.load(path)


# --- DOCTYPE detection ---


def test_detects_public_doctype(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    path = write_xml(
        b'<?xml version="1.0"?>\n'
        b'<!DOCTYPE article PUBLIC "-//NLM//DTD JATS//EN" "JATS-journalpublishing1-3.dtd">\n'
        b"<article/>"
    )

    document = loader.load(path)

    assert document.doctype is not None
    assert document.doctype.name == "article"
    assert document.doctype.public_id == "-//NLM//DTD JATS//EN"
    assert document.doctype.system_id == "JATS-journalpublishing1-3.dtd"
    assert document.doctype.has_internal_subset is False


def test_detects_system_only_doctype(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    path = write_xml(b'<?xml version="1.0"?>\n<!DOCTYPE root SYSTEM "root.dtd">\n<root/>')

    document = loader.load(path)

    assert document.doctype is not None
    assert document.doctype.public_id is None
    assert document.doctype.system_id == "root.dtd"


def test_detects_bare_doctype_with_no_external_id(
    loader: XmlLoader, write_xml: Callable[..., Path]
) -> None:
    path = write_xml(b"<!DOCTYPE root>\n<root/>")

    document = loader.load(path)

    assert document.doctype is not None
    assert document.doctype.name == "root"
    assert document.doctype.public_id is None
    assert document.doctype.system_id is None


def test_no_doctype_present(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    path = write_xml(b"<root/>")

    document = loader.load(path)

    assert document.doctype is None


def test_internal_subset_flagged_as_unsupported_construct(
    loader: XmlLoader, write_xml: Callable[..., Path]
) -> None:
    path = write_xml(b"<!DOCTYPE root [\n<!ATTLIST root a CDATA #IMPLIED>\n]>\n<root/>")

    document = loader.load(path)

    assert document.doctype is not None
    assert document.doctype.has_internal_subset is True
    unsupported = [
        d for d in document.diagnostics if d.category is DiagnosticCategory.UNSUPPORTED_CONSTRUCT
    ]
    assert len(unsupported) == 1


# --- large XML files ---


def test_loads_a_large_document(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    # Robustness/memory sanity check, not a performance benchmark
    # (performance work belongs to a later milestone per the roadmap).
    children = "".join(f'<item id="i{n}">value {n}</item>' for n in range(10_000))
    content = f'<?xml version="1.0"?><root>{children}</root>'.encode()
    path = write_xml(content)

    document = loader.load(path)

    assert len(document.root.children) == 10_000
    assert document.root.children[9999].text == "value 9999"


# --- unicode handling ---


def test_unicode_text_round_trips(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    content = '<?xml version="1.0" encoding="UTF-8"?><root>café 中文 \U0001f600</root>'.encode(
        "utf-8"
    )
    path = write_xml(content)

    document = loader.load(path)

    assert document.root.text == "café 中文 \U0001f600"


def test_unicode_attribute_value_round_trips(
    loader: XmlLoader, write_xml: Callable[..., Path]
) -> None:
    content = '<?xml version="1.0" encoding="UTF-8"?><root name="éèê"/>'.encode()
    path = write_xml(content)

    document = loader.load(path)

    assert get_attribute(document.root, "name") == "éèê"


# --- empty elements ---


def test_self_closing_element_has_no_text(
    loader: XmlLoader, write_xml: Callable[..., Path]
) -> None:
    path = write_xml(b"<root><empty/></root>")

    document = loader.load(path)

    assert document.root.children[0].text is None


def test_explicit_empty_element_has_no_text(
    loader: XmlLoader, write_xml: Callable[..., Path]
) -> None:
    path = write_xml(b"<root><empty></empty></root>")

    document = loader.load(path)

    assert document.root.children[0].text is None


# --- optional attributes ---


def test_missing_optional_attribute_returns_none(
    loader: XmlLoader, write_xml: Callable[..., Path]
) -> None:
    path = write_xml(b'<root><item name="present"/><item/></root>')

    document = loader.load(path)

    first, second = document.root.children
    assert get_attribute(first, "name") == "present"
    assert get_attribute(second, "name") is None


# --- mixed content (text/tail fidelity) ---


def test_tail_text_preserved(loader: XmlLoader, write_xml: Callable[..., Path]) -> None:
    path = write_xml(b"<p>before <b>bold</b> after</p>")

    document = loader.load(path)

    bold = document.root.children[0]
    assert document.root.text == "before "
    assert bold.text == "bold"
    assert bold.tail == " after"


# --- missing references (integrated end-to-end) ---


def test_dangling_reference_diagnostic_reported(
    loader: XmlLoader, write_xml: Callable[..., Path]
) -> None:
    path = write_xml(b'<root><aff id="aff1"/><xref rid="aff1"/><xref rid="missing"/></root>')

    document = loader.load(path)

    missing_ref_diagnostics = [
        d for d in document.diagnostics if d.category is DiagnosticCategory.MISSING_REFERENCE
    ]
    assert len(missing_ref_diagnostics) == 1
    assert "missing" in missing_ref_diagnostics[0].message


def test_custom_reference_attribute_names_configurable() -> None:
    custom_loader = XmlLoader(get_logger("test.custom"), reference_attribute_names=("target",))
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.xml"
        path.write_bytes(b'<root><a id="a1"/><b target="missing-target"/></root>')
        document = custom_loader.load(path)

    missing_ref_diagnostics = [
        d for d in document.diagnostics if d.category is DiagnosticCategory.MISSING_REFERENCE
    ]
    assert len(missing_ref_diagnostics) == 1


# --- logging integration ---


def test_logs_info_event_on_successful_load(write_xml: Callable[..., Path]) -> None:
    import logging

    logger_name_suffix = "test_logs_info_event_on_successful_load"
    from meca_engine.logging_.structured_logger import StructuredLogger

    class _ListHandler(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.records: list[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    underlying = logging.getLogger(f"meca_engine.test.{logger_name_suffix}")
    handler = _ListHandler()
    underlying.addHandler(handler)
    underlying.setLevel(logging.DEBUG)
    underlying.propagate = False

    xml_logger = StructuredLogger(f"test.{logger_name_suffix}")
    loader = XmlLoader(xml_logger)
    path = write_xml(b"<root/>")

    loader.load(path)

    assert len(handler.records) == 1
    assert handler.records[0].levelno == logging.INFO


# --- error-location formatting (unit-level, both attribute conventions) ---


def test_format_error_location_uses_position_attribute_when_present() -> None:
    class _FakePositionError(Exception):
        position = (3, 7)

    location = XmlLoader._format_error_location(_FakePositionError())

    assert location == " (line 3, column 7)"


def test_format_error_location_falls_back_to_lineno_offset_attributes() -> None:
    class _FakeExpatStyleError(Exception):
        lineno = 5
        offset = 12

    location = XmlLoader._format_error_location(_FakeExpatStyleError())

    assert location == " (line 5, column 12)"


def test_format_error_location_lineno_only_no_offset() -> None:
    class _FakeLineOnlyError(Exception):
        lineno = 9

    location = XmlLoader._format_error_location(_FakeLineOnlyError())

    assert location == " (line 9)"


def test_format_error_location_returns_empty_string_when_no_location_info() -> None:
    location = XmlLoader._format_error_location(Exception("plain"))

    assert location == ""
