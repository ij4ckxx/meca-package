"""Unit tests for meca_engine.extraction.metadata_extraction."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from meca_engine.extraction.metadata_extraction import extract_all_metadata
from meca_engine.extraction.parsed_model import (
    DiagnosticCategory,
    EncodingInfo,
    ParsedAttribute,
    ParsedDocument,
    ParsedElement,
)
from meca_engine.logging_.structured_logger import StructuredLogger

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = pytest.mark.unit

_ENCODING = EncodingInfo(declared_encoding=None, bom_encoding=None, effective_encoding="utf-8")


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def captured_logger(
    request: pytest.FixtureRequest,
) -> Iterator[tuple[StructuredLogger, _ListHandler]]:
    name = f"test.{request.node.name}"
    underlying = logging.getLogger(f"meca_engine.{name}")
    handler = _ListHandler()
    underlying.addHandler(handler)
    underlying.setLevel(logging.DEBUG)
    underlying.propagate = False
    yield StructuredLogger(name), handler
    underlying.removeHandler(handler)


def _document(root: ParsedElement) -> ParsedDocument:
    return ParsedDocument(source_path=Path("test.xml"), encoding=_ENCODING, doctype=None, root=root)


def test_combines_every_extractor_into_one_bundle(
    captured_logger: tuple[StructuredLogger, _ListHandler],
) -> None:
    logger, _ = captured_logger
    title = ParsedElement(tag="article-title", namespace_uri=None, text="A Title")
    title_group = ParsedElement(tag="title-group", namespace_uri=None, children=(title,))
    article_id = ParsedElement(
        tag="article-id",
        namespace_uri=None,
        attributes=(ParsedAttribute("pub-id-type", None, "doi"),),
        text="10.1/x",
    )
    article_meta = ParsedElement(
        tag="article-meta", namespace_uri=None, children=(article_id, title_group)
    )
    root = ParsedElement(
        tag="article",
        namespace_uri=None,
        children=(ParsedElement(tag="front", namespace_uri=None, children=(article_meta,)),),
    )

    bundle = extract_all_metadata(_document(root), logger)

    assert bundle.article.title == "A Title"
    # No <journal-meta> section is present in this fixture, so the
    # journal extractor still contributes its own missing-title
    # diagnostic — this bundle-level assertion only confirms article
    # metadata came through, not that every extractor found everything.
    assert len(bundle.diagnostics) == 1
    assert bundle.diagnostics[0].category is DiagnosticCategory.MISSING_REQUIRED_VALUE


def test_diagnostics_from_every_extractor_are_flattened(
    captured_logger: tuple[StructuredLogger, _ListHandler],
) -> None:
    logger, _ = captured_logger
    root = ParsedElement(tag="article", namespace_uri=None)

    bundle = extract_all_metadata(_document(root), logger)

    # Missing <article-meta> yields one diagnostic from the article
    # extractor; the journal extractor also reports a missing title.
    assert len(bundle.diagnostics) == 2


def test_logs_start_and_completion_for_every_extractor(
    captured_logger: tuple[StructuredLogger, _ListHandler],
) -> None:
    logger, handler = captured_logger
    root = ParsedElement(tag="article", namespace_uri=None)

    extract_all_metadata(_document(root), logger)

    messages = [record.getMessage() for record in handler.records]
    for stage in (
        "article",
        "contributor",
        "journal",
        "workflow",
        "custom",
        "asset",
        "cross-reference",
    ):
        assert any(stage in message for message in messages)
    assert any("Starting" in message for message in messages)
    assert any("Completed" in message for message in messages)


def test_emits_a_performance_event_per_extractor(
    captured_logger: tuple[StructuredLogger, _ListHandler],
) -> None:
    from meca_engine.constants import LogCategory
    from meca_engine.logging_.record_fields import EXTRA_CATEGORY

    logger, handler = captured_logger
    root = ParsedElement(tag="article", namespace_uri=None)

    extract_all_metadata(_document(root), logger)

    performance_events = [
        record
        for record in handler.records
        if getattr(record, EXTRA_CATEGORY, None) == LogCategory.PERFORMANCE.value
    ]
    assert len(performance_events) == 7
