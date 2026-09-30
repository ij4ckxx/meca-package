"""Journal transformation — Milestone 5B.

Builds :class:`~meca_engine.model.article.JournalMeta` from Milestone 4's
extracted journal metadata. Every field is copied verbatim (LLD:
"JournalMeta... copied verbatim") — this transformer performs no lookup
against `config.registry.ConfigRegistry`/`JournalConfig`, since none of
`JournalMeta`'s own fields (title, ISSNs, publisher name, abbreviated
titles) are business-value *configuration* — they are per-article source
values. "No hard-coded values" is satisfied by construction: nothing here
is a per-journal constant a naive implementation might be tempted to
inline (e.g. a hard-coded publisher name) — every value traces back to
the extracted source metadata, never a literal in this module.

**Correction (Milestone 9)**: ``journal_ids``/``volume``/``issue``/
``fpage``/``lpage`` are now also copied verbatim — previously extracted
at Milestone 4 but never wired past this transformer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.model.article import JournalMeta

if TYPE_CHECKING:
    from meca_engine.extraction.metadata_models import JournalMetadata


def build_journal_meta(journal_metadata: JournalMetadata) -> JournalMeta:
    """Build the article's journal metadata.

    Args:
        journal_metadata: Milestone 4's extracted journal metadata.

    Returns:
        The built :class:`~meca_engine.model.article.JournalMeta`.
        ``journal_title``/``publisher_name`` fall back to an empty
        string when absent from the source (non-optional ICAM fields);
        ``issn_ppub``/``issn_epub`` remain ``None`` when the journal has
        no print or electronic ISSN, respectively.
    """
    issn_ppub = None
    issn_epub = None
    for pub_type, value in journal_metadata.issns:
        if pub_type == "ppub":
            issn_ppub = value
        elif pub_type == "epub":
            issn_epub = value

    abbrev_titles = tuple(
        (abbrev_type, value)
        for abbrev_type, value in journal_metadata.abbrev_titles
        if abbrev_type is not None
    )
    journal_ids = tuple(
        (id_type, value) for id_type, value in journal_metadata.journal_ids if id_type is not None
    )

    return JournalMeta(
        journal_title=journal_metadata.journal_title or "",
        issn_ppub=issn_ppub,
        issn_epub=issn_epub,
        publisher_name=journal_metadata.publisher_name or "",
        abbrev_titles=abbrev_titles,
        journal_ids=journal_ids,
        volume=journal_metadata.volume,
        issue=journal_metadata.issue,
        fpage=journal_metadata.fpage,
        lpage=journal_metadata.lpage,
    )
