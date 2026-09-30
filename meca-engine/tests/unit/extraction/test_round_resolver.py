"""Unit tests for meca_engine.extraction.round_resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from meca_engine.exceptions import RoundResolutionError
from meca_engine.extraction.parsed_model import (
    EncodingInfo,
    ParsedAttribute,
    ParsedDocument,
    ParsedElement,
)
from meca_engine.extraction.round_resolver import resolve_rounds
from meca_engine.model.article import RoundInfo

pytestmark = pytest.mark.unit

_ENCODING = EncodingInfo(declared_encoding=None, bom_encoding=None, effective_encoding="utf-8")


def _document(root: ParsedElement) -> ParsedDocument:
    return ParsedDocument(source_path=Path("test.xml"), encoding=_ENCODING, doctype=None, root=root)


def _version(vocab_identifier: str | None, version_type: str | None) -> ParsedElement:
    attributes = []
    if vocab_identifier is not None:
        attributes.append(ParsedAttribute("vocab-identifier", None, vocab_identifier))
    if version_type is not None:
        attributes.append(ParsedAttribute("article-version-type", None, version_type))
    return ParsedElement(tag="article-version", namespace_uri=None, attributes=tuple(attributes))


def test_no_article_version_returns_empty_index() -> None:
    root = ParsedElement(tag="article", namespace_uri=None)

    assert resolve_rounds(_document(root)) == ((), ())


def test_single_article_version_is_latest() -> None:
    version = _version("snapshots/20_authorrevision/x.xml", "Original")
    root = ParsedElement(tag="article", namespace_uri=None, children=(version,))

    rounds, warnings = resolve_rounds(_document(root))

    assert rounds == (RoundInfo(label="Original", sequence_number=20, is_latest=True),)
    assert warnings == ()


def test_multiple_article_versions_ordered_by_sequence_and_latest_flagged() -> None:
    v1 = _version("snapshots/9_x/a.xml", "Original")
    v2 = _version("snapshots/17_x/b.xml", "Original")
    root = ParsedElement(tag="article", namespace_uri=None, children=(v1, v2))

    rounds, _ = resolve_rounds(_document(root))

    assert [r.sequence_number for r in rounds] == [9, 17]
    assert [r.is_latest for r in rounds] == [False, True]


# --- Milestone 11 (ADR-033): malformed individual elements are skipped, not raised ---


def test_missing_vocab_identifier_is_skipped_with_a_warning() -> None:
    version = _version(None, "Original")
    root = ParsedElement(tag="article", namespace_uri=None, children=(version,))

    rounds, warnings = resolve_rounds(_document(root))

    assert rounds == ()
    assert len(warnings) == 1
    assert warnings[0].code == "BR010_MALFORMED_ARTICLE_VERSION_SKIPPED"
    assert warnings[0].is_recovery is True


def test_malformed_vocab_identifier_is_skipped_with_a_warning() -> None:
    version = _version("not-the-right-format", "Original")
    root = ParsedElement(tag="article", namespace_uri=None, children=(version,))

    rounds, warnings = resolve_rounds(_document(root))

    assert rounds == ()
    assert len(warnings) == 1
    assert warnings[0].code == "BR010_MALFORMED_ARTICLE_VERSION_SKIPPED"


def test_missing_article_version_type_is_skipped_with_a_warning() -> None:
    version = _version("snapshots/1_x/a.xml", None)
    root = ParsedElement(tag="article", namespace_uri=None, children=(version,))

    rounds, warnings = resolve_rounds(_document(root))

    assert rounds == ()
    assert len(warnings) == 1
    assert warnings[0].code == "BR010_MALFORMED_ARTICLE_VERSION_SKIPPED"


def test_one_malformed_element_alongside_a_valid_one_still_resolves() -> None:
    valid = _version("snapshots/9_x/a.xml", "Original")
    malformed = _version(None, "R1")
    root = ParsedElement(tag="article", namespace_uri=None, children=(valid, malformed))

    rounds, warnings = resolve_rounds(_document(root))

    assert rounds == (RoundInfo(label="Original", sequence_number=9, is_latest=True),)
    assert len(warnings) == 1


# --- Milestone 11 (ADR-033): duplicate-sequence handling ---


def test_duplicate_sequence_with_same_label_is_deduped_with_a_warning() -> None:
    """Real evidence (bcj-2025-3400): repeated autosave events share a
    sequence_number and label — collapsed to one round, not an error."""
    v1 = _version("snapshots/8_x/a.xml", "Original")
    v2 = _version("snapshots/8_x/b.xml", "Original")
    v3 = _version("snapshots/8_x/c.xml", "Original")
    root = ParsedElement(tag="article", namespace_uri=None, children=(v1, v2, v3))

    rounds, warnings = resolve_rounds(_document(root))

    assert rounds == (RoundInfo(label="Original", sequence_number=8, is_latest=True),)
    assert len(warnings) == 1
    assert warnings[0].code == "BR010_DUPLICATE_SEQUENCE_DEDUPED"
    assert warnings[0].is_recovery is True
    assert warnings[0].context_dict()["duplicate_count"] == "3"


def test_duplicate_sequence_number_with_conflicting_labels_still_raises() -> None:
    """A genuine, unresolvable ambiguity (ADR-013) — never guessed."""
    v1 = _version("snapshots/5_x/a.xml", "Original")
    v2 = _version("snapshots/5_x/b.xml", "R1")
    root = ParsedElement(tag="article", namespace_uri=None, children=(v1, v2))

    with pytest.raises(RoundResolutionError):
        resolve_rounds(_document(root))


def test_error_carries_article_id_context() -> None:
    v1 = _version("snapshots/5_x/a.xml", "Original")
    v2 = _version("snapshots/5_x/b.xml", "R1")
    root = ParsedElement(tag="article", namespace_uri=None, children=(v1, v2))

    with pytest.raises(RoundResolutionError) as exc_info:
        resolve_rounds(_document(root), article_id="cs-2025-0001")

    assert exc_info.value.article_id == "cs-2025-0001"
