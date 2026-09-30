"""Unit tests for meca_engine.transform.identity_transformer."""

from __future__ import annotations

import pytest

from meca_engine.extraction.metadata_models import (
    ArticleIdentifier,
    ArticleMetadata,
    JournalMetadata,
)
from meca_engine.transform.identity_transformer import build_identity

pytestmark = pytest.mark.unit


def test_builds_identity_from_extracted_metadata() -> None:
    article_metadata = ArticleMetadata(
        identifiers=(
            ArticleIdentifier(id_type="publisher-id", value="CS-2025-0001"),
            ArticleIdentifier(id_type="doi", value="CS-2025-0001"),
        )
    )
    journal_metadata = JournalMetadata(journal_id="CS")

    identity = build_identity(
        article_metadata,
        journal_metadata,
        article_id="cs-2025-0001",
        source_object_key="cs-2025-0001/cs-2025-0001.xml",
    )

    assert identity.article_id == "cs-2025-0001"
    assert identity.publisher_id_value == "CS-2025-0001"
    assert identity.doi_article_id_value == "CS-2025-0001"
    assert identity.journal_id == "cs"
    assert identity.source_object_key == "cs-2025-0001/cs-2025-0001.xml"


def test_journal_id_is_lower_cased_per_adr_028() -> None:
    identity = build_identity(
        ArticleMetadata(),
        JournalMetadata(journal_id="CS"),
        article_id="x",
        source_object_key="x",
    )

    assert identity.journal_id == "cs"


def test_missing_identifiers_produce_empty_strings_not_none() -> None:
    identity = build_identity(
        ArticleMetadata(), JournalMetadata(), article_id="x", source_object_key="x"
    )

    assert identity.publisher_id_value == ""
    assert identity.doi_article_id_value == ""
    assert identity.journal_id == ""


def test_does_not_generate_a_doi_only_copies_source_field() -> None:
    article_metadata = ArticleMetadata(
        identifiers=(ArticleIdentifier(id_type="doi", value="raw-source-value"),)
    )

    identity = build_identity(
        article_metadata, JournalMetadata(), article_id="x", source_object_key="x"
    )

    assert identity.doi_article_id_value == "raw-source-value"


def test_ignores_other_identifier_types() -> None:
    article_metadata = ArticleMetadata(
        identifiers=(ArticleIdentifier(id_type="pmid", value="12345"),)
    )

    identity = build_identity(
        article_metadata, JournalMetadata(), article_id="x", source_object_key="x"
    )

    assert identity.publisher_id_value == ""
    assert identity.doi_article_id_value == ""
