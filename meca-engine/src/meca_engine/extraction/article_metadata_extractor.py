"""Article-level metadata extraction — Milestone 4 (extended in Milestone 5B).

Reads article-id, title, article-type, language, history/pub-date,
display-channel/heading subject, and abstract values out of a
:class:`~meca_engine.extraction.parsed_model.ParsedDocument`.
A pure function: no logging, no I/O, no exceptions raised for missing
fields. A missing field is reported as a diagnostic (never an exception)
when it is one of the two source values every article is expected to
carry (a title, at least one article-id) — anything less clear-cut than
that is left as ``None``/empty with no diagnostic, rather than guessing
at what else might be "required". Does not normalize, classify, or
validate any value it finds.

**Correction (Milestone 9)**: ``<pub-date>`` carries its variant in a
``pub-type`` attribute (``"epub"``/``"ppub"``), not ``date-type`` —
``_extract_date`` now checks both, so ``pub_dates`` entries carry their
real type instead of always reading back as ``None``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.extraction.metadata_models import (
    AbstractRecord,
    ArticleIdentifier,
    ArticleMetadata,
    DateRecord,
)
from meca_engine.extraction.navigation import (
    XML_NAMESPACE_URI,
    find_all,
    find_first,
    get_attribute,
    get_text,
)
from meca_engine.extraction.parsed_model import (
    DiagnosticCategory,
    DiagnosticSeverity,
    ParseDiagnostic,
)

if TYPE_CHECKING:
    from meca_engine.extraction.parsed_model import ParsedDocument, ParsedElement


def _extract_identifiers(article_meta: ParsedElement) -> tuple[ArticleIdentifier, ...]:
    return tuple(
        ArticleIdentifier(
            id_type=get_attribute(element, "pub-id-type"),
            value=get_text(element, recursive=True),
        )
        for element in find_all(article_meta, "article-id")
    )


def _extract_subject(subj_group: ParsedElement) -> str | None:
    subject_element = find_first(subj_group, "subject", recursive=False)
    return get_text(subject_element, recursive=True) if subject_element is not None else None


def _extract_date(element: ParsedElement) -> DateRecord:
    year_element = find_first(element, "year", recursive=False)
    month_element = find_first(element, "month", recursive=False)
    day_element = find_first(element, "day", recursive=False)
    # `<date>` (history) carries `date-type`; `<pub-date>` carries `pub-type`
    # instead — both are read here so `pub_dates` entries aren't silently
    # left with `date_type=None` (Milestone 9 correction).
    date_type = get_attribute(element, "date-type")
    if date_type is None:
        date_type = get_attribute(element, "pub-type")
    return DateRecord(
        date_type=date_type,
        year=get_text(year_element, recursive=True) if year_element is not None else None,
        month=get_text(month_element, recursive=True) if month_element is not None else None,
        day=get_text(day_element, recursive=True) if day_element is not None else None,
    )


def _extract_subject_groups(article_meta: ParsedElement) -> tuple[str | None, tuple[str, ...]]:
    display_channel_subject = None
    heading_subjects: list[str] = []
    for subj_group in find_all(article_meta, "subj-group"):
        subject = _extract_subject(subj_group)
        if subject is None:
            continue
        subj_group_type = get_attribute(subj_group, "subj-group-type")
        if subj_group_type == "display-channel":
            display_channel_subject = subject
        elif subj_group_type == "heading":
            heading_subjects.append(subject)
    return display_channel_subject, tuple(heading_subjects)


def _extract_copyright(article_meta: ParsedElement) -> tuple[str | None, str | None]:
    permissions = find_first(article_meta, "permissions")
    if permissions is None:
        return None, None
    statement_element = find_first(permissions, "copyright-statement")
    year_element = find_first(permissions, "copyright-year")
    copyright_statement = (
        get_text(statement_element, recursive=True) if statement_element is not None else None
    )
    copyright_year = get_text(year_element, recursive=True) if year_element is not None else None
    return copyright_statement, copyright_year


def _extract_keywords(article_meta: ParsedElement) -> tuple[str, ...]:
    texts = (get_text(element, recursive=True) for element in find_all(article_meta, "kwd"))
    return tuple(text for text in texts if text)


def _extract_counts(
    article_meta: ParsedElement,
) -> tuple[str | None, str | None, str | None, str | None, str | None, str | None]:
    counts = find_first(article_meta, "counts")
    if counts is None:
        return None, None, None, None, None, None

    def _count(tag: str) -> str | None:
        element = find_first(counts, tag, recursive=False)
        return get_attribute(element, "count") if element is not None else None

    return (
        _count("word-count"),
        _count("ref-count"),
        _count("fig-count"),
        _count("table-count"),
        _count("equation-count"),
        _count("page-count"),
    )


def _extract_language(element: ParsedElement) -> str | None:
    return get_attribute(element, "lang", namespace_uri=XML_NAMESPACE_URI) or get_attribute(
        element, "lang"
    )


def _extract_abstracts(article_meta: ParsedElement) -> tuple[AbstractRecord, ...]:
    return tuple(
        AbstractRecord(
            text=get_text(element, recursive=True),
            abstract_type=get_attribute(element, "abstract-type"),
            language=_extract_language(element),
        )
        for element in find_all(article_meta, "abstract")
    )


def extract_article_metadata(
    document: ParsedDocument,
) -> tuple[ArticleMetadata, tuple[ParseDiagnostic, ...]]:
    """Extract article-level metadata from a parsed document.

    Args:
        document: The parsed document to read from.

    Returns:
        The extracted
        :class:`~meca_engine.extraction.metadata_models.ArticleMetadata`,
        alongside any diagnostics raised (a missing title or a missing
        article-id). Every field is ``None``/empty when the
        corresponding source structure isn't present — this function
        never raises for a missing field.
    """
    article_meta = find_first(document.root, "article-meta")
    if article_meta is None:
        return ArticleMetadata(), (
            ParseDiagnostic(
                severity=DiagnosticSeverity.WARNING,
                category=DiagnosticCategory.MISSING_REQUIRED_VALUE,
                message="No <article-meta> element found in the document",
            ),
        )

    diagnostics: list[ParseDiagnostic] = []
    identifiers = _extract_identifiers(article_meta)
    if not identifiers:
        diagnostics.append(
            ParseDiagnostic(
                severity=DiagnosticSeverity.WARNING,
                category=DiagnosticCategory.MISSING_REQUIRED_VALUE,
                message="No <article-id> found under <article-meta>",
            )
        )

    title_element = find_first(article_meta, "article-title")
    title = get_text(title_element, recursive=True) if title_element is not None else None
    if not title:
        diagnostics.append(
            ParseDiagnostic(
                severity=DiagnosticSeverity.WARNING,
                category=DiagnosticCategory.MISSING_REQUIRED_VALUE,
                message="No <article-title> found under <article-meta>",
            )
        )

    subtitle_element = find_first(article_meta, "subtitle")
    history = find_first(article_meta, "history")
    history_dates = (
        tuple(_extract_date(element) for element in find_all(history, "date"))
        if history is not None
        else ()
    )
    pub_dates = tuple(_extract_date(element) for element in find_all(article_meta, "pub-date"))

    display_channel_subject, heading_subjects = _extract_subject_groups(article_meta)
    copyright_statement, copyright_year = _extract_copyright(article_meta)
    keywords = _extract_keywords(article_meta)
    funding_statements = tuple(
        get_text(element, recursive=True) for element in find_all(article_meta, "funding-group")
    )
    word_count, ref_count, fig_count, table_count, equation_count, page_count = _extract_counts(
        article_meta
    )
    abstracts = _extract_abstracts(article_meta)

    metadata = ArticleMetadata(
        identifiers=identifiers,
        title=title,
        subtitle=(
            get_text(subtitle_element, recursive=True) if subtitle_element is not None else None
        ),
        article_type=get_attribute(document.root, "article-type"),
        publication_status=get_attribute(article_meta, "publication-status"),
        language=get_attribute(document.root, "lang"),
        history_dates=history_dates,
        pub_dates=pub_dates,
        display_channel_subject=display_channel_subject,
        heading_subjects=heading_subjects,
        copyright_statement=copyright_statement,
        copyright_year=copyright_year,
        keywords=keywords,
        funding_statements=funding_statements,
        word_count=word_count,
        ref_count=ref_count,
        fig_count=fig_count,
        table_count=table_count,
        equation_count=equation_count,
        page_count=page_count,
        abstracts=abstracts,
    )
    return metadata, tuple(diagnostics)
