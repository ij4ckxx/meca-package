"""Unit tests for meca_engine.extraction.workflow_metadata_extractor."""

from __future__ import annotations

from pathlib import Path

import pytest

from meca_engine.extraction.parsed_model import EncodingInfo, ParsedDocument, ParsedElement
from meca_engine.extraction.workflow_metadata_extractor import extract_workflow_metadata

pytestmark = pytest.mark.unit

_ENCODING = EncodingInfo(declared_encoding=None, bom_encoding=None, effective_encoding="utf-8")


def _document(root: ParsedElement) -> ParsedDocument:
    return ParsedDocument(source_path=Path("test.xml"), encoding=_ENCODING, doctype=None, root=root)


def test_flattens_event_direct_children_verbatim() -> None:
    event = ParsedElement(
        tag="event",
        namespace_uri=None,
        children=(
            ParsedElement(tag="action", namespace_uri=None, text="submitted"),
            ParsedElement(tag="date", namespace_uri=None, text="2025-01-15"),
        ),
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(event,))

    metadata, diagnostics = extract_workflow_metadata(_document(root))

    assert len(metadata.events) == 1
    assert metadata.events[0].event_tag == "event"
    assert metadata.events[0].fields == (("action", "submitted"), ("date", "2025-01-15"))
    assert metadata.events[0].raw_element is event
    assert diagnostics == ()


def test_recognizes_every_default_tag_name() -> None:
    root = ParsedElement(
        tag="root",
        namespace_uri=None,
        children=(
            ParsedElement(tag="event", namespace_uri=None),
            ParsedElement(tag="log-entry", namespace_uri=None),
            ParsedElement(tag="stage", namespace_uri=None),
        ),
    )

    metadata, _ = extract_workflow_metadata(_document(root))

    assert len(metadata.events) == 3


def test_custom_event_tag_names() -> None:
    root = ParsedElement(
        tag="root", namespace_uri=None, children=(ParsedElement(tag="log", namespace_uri=None),)
    )

    metadata, _ = extract_workflow_metadata(_document(root), event_tag_names=("log",))

    assert len(metadata.events) == 1
    assert metadata.events[0].event_tag == "log"


def test_no_matching_elements_produces_no_events() -> None:
    root = ParsedElement(tag="root", namespace_uri=None)

    metadata, _ = extract_workflow_metadata(_document(root))

    assert metadata.events == ()
