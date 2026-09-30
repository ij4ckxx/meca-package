"""Identity transformation — Milestone 5B.

Builds :class:`~meca_engine.model.article.ArticleIdentity` from Milestone
4's extracted article/journal metadata plus two values only Milestone 2's
staging layer knows (``article_id``, the exact input-folder string per
BR-003, and ``source_object_key``, the staged root's S3 key). Neither of
those two is derivable from XML content — this transformer never guesses
them; they must be supplied by the caller.

**Does not generate a DOI.** ``doi_article_id_value`` is the verbatim
source ``article-id[@pub-id-type=doi]`` field (BR-058's *input*), copied
unchanged — DOI generation itself (BR-058's formula) is
`generators.article_xml.doi_builder`'s job, a later milestone.

``journal_id`` is derived from the verbatim ``journal-id[@journal-id-type=
publisher-id]`` value by lower-casing it (ADR-028's documented config
lookup-key convention, per
:class:`~meca_engine.config.schema.JournalConfig`'s own docstring) — a
generic string operation, not a per-journal hard-coded table. This
transformer never requires a populated `JournalConfig` to exist for that
key; it only computes the key itself, so it remains testable against the
3 real reference packages even before config/journals/ is populated (see
the Milestone 5B Architecture Compliance Report).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.model.article import ArticleIdentity

if TYPE_CHECKING:
    from meca_engine.extraction.metadata_models import ArticleMetadata, JournalMetadata

_DOI_ID_TYPE = "doi"
_PUBLISHER_ID_TYPE = "publisher-id"


def build_identity(
    article_metadata: ArticleMetadata,
    journal_metadata: JournalMetadata,
    *,
    article_id: str,
    source_object_key: str,
) -> ArticleIdentity:
    """Build the article's identity.

    Args:
        article_metadata: Milestone 4's extracted article metadata.
        journal_metadata: Milestone 4's extracted journal metadata.
        article_id: The exact input-folder string (BR-003) — supplied by
            the caller; not derivable from XML content.
        source_object_key: The staged root XML's S3 key, for
            traceability/logging — supplied by the caller.

    Returns:
        The built :class:`~meca_engine.model.article.ArticleIdentity`.
        ``publisher_id_value``/``doi_article_id_value`` are empty strings
        when the corresponding source ``article-id`` is absent — never
        ``None``, matching the ICAM's non-optional field type; a missing
        DOI source field is a data-quality fact for a later validation
        stage to flag, not this transformer's concern.
    """
    publisher_id_value = ""
    doi_article_id_value = ""
    for identifier in article_metadata.identifiers:
        if identifier.id_type == _PUBLISHER_ID_TYPE:
            publisher_id_value = identifier.value
        elif identifier.id_type == _DOI_ID_TYPE:
            doi_article_id_value = identifier.value

    journal_id = journal_metadata.journal_id.lower() if journal_metadata.journal_id else ""

    return ArticleIdentity(
        article_id=article_id,
        publisher_id_value=publisher_id_value,
        doi_article_id_value=doi_article_id_value,
        journal_id=journal_id,
        source_object_key=source_object_key,
    )
