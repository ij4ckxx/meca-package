"""Journal-level metadata extraction — Milestone 4 (extended in Milestone 5B).

Reads journal title/id, ISSN, publisher, volume/issue/page, and
DOI-related identifier values out of a
:class:`~meca_engine.extraction.parsed_model.ParsedDocument`. A pure
function: no logging, no I/O, no exceptions for missing fields.

**Correction (Milestone 9)**: ``journal_id`` only ever captured the
first ``journal-id[@journal-id-type="publisher-id"]`` match (needed for
ADR-028 config lookup) — a second real ``journal-id`` (e.g.
``journal-id-type="nlm-ta"``) always went uncaptured. ``journal_ids``
now preserves every ``journal-id``/type pair found, the same pattern
already used for ``abbrev_titles``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.extraction.article_metadata_extractor import extract_article_metadata
from meca_engine.extraction.metadata_models import JournalMetadata
from meca_engine.extraction.navigation import find_all, find_first, get_attribute, get_text
from meca_engine.extraction.parsed_model import (
    DiagnosticCategory,
    DiagnosticSeverity,
    ParseDiagnostic,
)

if TYPE_CHECKING:
    from meca_engine.extraction.parsed_model import ParsedDocument


def extract_journal_metadata(
    document: ParsedDocument,
) -> tuple[JournalMetadata, tuple[ParseDiagnostic, ...]]:
    """Extract journal-level metadata from a parsed document.

    Args:
        document: The parsed document to read from.

    Returns:
        The extracted
        :class:`~meca_engine.extraction.metadata_models.JournalMetadata`,
        alongside any diagnostics raised (a missing journal title).
        ``doi_related_ids`` is populated by re-running
        :func:`~meca_engine.extraction.article_metadata_extractor.extract_article_metadata`
        and filtering its identifiers to ``id_type == "doi"`` — a
        convenience grouping, not a second independent extraction.
    """
    journal_meta = find_first(document.root, "journal-meta")
    article_meta = find_first(document.root, "article-meta")

    journal_id = None
    journal_ids: tuple[tuple[str | None, str], ...] = ()
    if journal_meta is not None:
        journal_ids = tuple(
            (get_attribute(element, "journal-id-type"), get_text(element, recursive=True))
            for element in find_all(journal_meta, "journal-id")
        )
        for id_type, id_value in journal_ids:
            if id_type == "publisher-id":
                journal_id = id_value
                break

    title_element = find_first(journal_meta, "journal-title") if journal_meta is not None else None
    journal_title = get_text(title_element, recursive=True) if title_element is not None else None

    issns = (
        tuple(
            (get_attribute(element, "pub-type"), get_text(element, recursive=True))
            for element in find_all(journal_meta, "issn")
        )
        if journal_meta is not None
        else ()
    )

    abbrev_titles = (
        tuple(
            (get_attribute(element, "abbrev-type"), get_text(element, recursive=True))
            for element in find_all(journal_meta, "abbrev-journal-title")
        )
        if journal_meta is not None
        else ()
    )

    publisher_name_element = (
        find_first(journal_meta, "publisher-name") if journal_meta is not None else None
    )
    publisher_name = (
        get_text(publisher_name_element, recursive=True)
        if publisher_name_element is not None
        else None
    )

    def _field(tag: str) -> str | None:
        if article_meta is None:
            return None
        element = find_first(article_meta, tag)
        return get_text(element, recursive=True) if element is not None else None

    article_metadata, _ = extract_article_metadata(document)
    doi_related_ids = tuple(
        identifier.value
        for identifier in article_metadata.identifiers
        if identifier.id_type == "doi"
    )

    diagnostics: tuple[ParseDiagnostic, ...] = ()
    if not journal_title:
        diagnostics = (
            ParseDiagnostic(
                severity=DiagnosticSeverity.WARNING,
                category=DiagnosticCategory.MISSING_REQUIRED_VALUE,
                message="No <journal-title> found under <journal-meta>",
            ),
        )

    metadata = JournalMetadata(
        journal_title=journal_title,
        journal_id=journal_id,
        issns=issns,
        publisher_name=publisher_name,
        abbrev_titles=abbrev_titles,
        journal_ids=journal_ids,
        volume=_field("volume"),
        issue=_field("issue"),
        fpage=_field("fpage"),
        lpage=_field("lpage"),
        elocation_id=_field("elocation-id"),
        doi_related_ids=doi_related_ids,
    )
    return metadata, diagnostics
