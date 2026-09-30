"""Metadata Extraction Layer output types — Milestone 4.

These types are a distinct, intermediate layer between the generic Parsed
Object Model (Milestone 3) and the eventual Internal Canonical Article
Model (ICAM, Milestone 5+). They identify and hold *extracted* source
values — grouped and named for what they represent — without applying
any business-rule transformation, normalization, or publishing-semantic
interpretation. Field values are preserved verbatim from the source; no
renaming of *content*, only of the structural grouping itself.

All types are frozen dataclasses, consistent with every other model in
this codebase (Milestones 2 and 3 alike).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meca_engine.extraction.file_relationships import FileReference
    from meca_engine.extraction.parsed_model import ParsedElement, ParseDiagnostic


@dataclass(frozen=True)
class ArticleIdentifier:
    """One article-id value, with its declared type preserved as-is.

    Attributes:
        id_type: The source ``pub-id-type`` (or equivalent) value, exactly
            as written (e.g. ``"doi"``, ``"publisher-id"``) — never
            classified or validated here.
        value: The identifier's literal text.
    """

    id_type: str | None
    value: str


@dataclass(frozen=True)
class DateRecord:
    """One date value, with its component parts preserved separately.

    Attributes:
        date_type: The source date-type value (e.g. ``"received"``,
            ``"accepted"``, ``"pub"``), exactly as written.
        year: The year component, if present, as source text.
        month: The month component, if present, as source text.
        day: The day component, if present, as source text.
    """

    date_type: str | None
    year: str | None
    month: str | None
    day: str | None


@dataclass(frozen=True)
class AbstractRecord:
    """One abstract section, preserved as found.

    Added in Milestone 5C (Architecture Review §6.11) for Abstract Support.
    JATS permits more than one ``<abstract>`` under ``article-meta``
    (e.g. a plain-language summary alongside the main abstract), so this
    is a record type collected into a tuple rather than a single field —
    though none of the 3 real reference packages inspected exhibit more
    than one.

    Attributes:
        text: The abstract's full flattened text content, preserved
            verbatim via :func:`~meca_engine.extraction.navigation.get_text`
            — no rewriting or reformatting.
        abstract_type: The source ``abstract-type`` attribute value,
            exactly as written, if present. Not observed on any of the 3
            real reference packages.
        language: The source ``xml:lang`` value, if present (checked
            namespace-aware, consistent with this codebase's ``xml:id``
            handling, with a defensive fallback to an unprefixed ``lang``
            attribute). Not observed on any real reference package.
    """

    text: str
    abstract_type: str | None = None
    language: str | None = None


@dataclass(frozen=True)
class ArticleMetadata:
    """Article-level metadata extracted from a parsed document.

    Attributes:
        identifiers: Every article-id value found, in document order.
        title: The article title, if found.
        subtitle: The article subtitle, if found.
        article_type: The source ``article-type`` attribute value, exactly
            as written.
        publication_status: A best-effort source value describing
            publication status, if a recognizable field for it was
            present. No confirmed source-system convention for this field
            was identified during analysis; this is preserved as found,
            not inferred — see the Milestone 4 Architecture Compliance
            Report for the open question this leaves for Milestone 5.
        language: The source ``xml:lang`` (or equivalent) value, if
            present.
        history_dates: Every history/event date found (received, revised,
            accepted, and similar), in document order.
        pub_dates: Every publication date found, in document order.
        display_channel_subject: The text of
            ``subj-group[@subj-group-type=display-channel]/subject``, if
            found. Added in Milestone 5B, same additive rationale as
            :class:`JournalMetadata`'s ``journal_id`` — a distinct source
            field from ``article_type`` (the root element's
            ``article-type`` attribute), confirmed by real
            reference-package inspection (e.g. ``article_type ==
            "research-article"`` while this field's text is
            ``"Research Article"``).
        heading_subjects: The text of every
            ``subj-group[@subj-group-type=heading]/subject``, in document
            order.
        copyright_statement: The verbatim
            ``permissions/copyright-statement`` text, if found.
        copyright_year: The verbatim ``permissions/copyright-year`` text,
            if found.
        keywords: Every non-empty ``kwd-group/kwd`` text value, in
            document order.
        funding_statements: Every ``funding-group`` element's fully
            flattened text, in document order — not decomposed into its
            (deeply nested, source-system-specific) ``award-group``
            structure, matching this layer's "identify, don't interpret"
            boundary.
        word_count: The ``counts/word-count/@count`` value, if found.
        ref_count: The ``counts/ref-count/@count`` value, if found.
        fig_count: The ``counts/fig-count/@count`` value, if found.
        table_count: The ``counts/table-count/@count`` value, if found.
            Added Milestone 9 (previously genuinely absent at every
            layer).
        equation_count: The ``counts/equation-count/@count`` value, if
            found.
        page_count: The ``counts/page-count/@count`` value, if found.
        abstracts: Every ``abstract`` element found under ``article-meta``,
            in document order. Added in Milestone 5C — see
            :class:`AbstractRecord`.
    """

    identifiers: tuple[ArticleIdentifier, ...] = field(default_factory=tuple)
    title: str | None = None
    subtitle: str | None = None
    article_type: str | None = None
    publication_status: str | None = None
    language: str | None = None
    history_dates: tuple[DateRecord, ...] = field(default_factory=tuple)
    pub_dates: tuple[DateRecord, ...] = field(default_factory=tuple)
    display_channel_subject: str | None = None
    heading_subjects: tuple[str, ...] = field(default_factory=tuple)
    copyright_statement: str | None = None
    copyright_year: str | None = None
    keywords: tuple[str, ...] = field(default_factory=tuple)
    funding_statements: tuple[str, ...] = field(default_factory=tuple)
    word_count: str | None = None
    ref_count: str | None = None
    fig_count: str | None = None
    table_count: str | None = None
    equation_count: str | None = None
    page_count: str | None = None
    abstracts: tuple[AbstractRecord, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AffiliationRecord:
    """One affiliation entry, preserved as found.

    Attributes:
        element_id: The affiliation element's own id, if present (used by
            contributors to reference it).
        label: The affiliation's display label (e.g. "1"), if a
            separately-tagged ``<label>`` child was present.
        department: The department/division name text, if a recognizable
            field was present.
        institution: The institution name text, if a recognizable field
            was present.
        city: The city text, if a recognizable field was present.
        state: The state/province text, if a recognizable field was
            present.
        country: The country text, if a recognizable field was present.
        raw_text: The affiliation's full flattened text content, as a
            fallback for source structures with no separately-tagged
            fields at all.
    """

    element_id: str | None
    label: str | None
    department: str | None
    institution: str | None
    city: str | None
    state: str | None
    country: str | None
    raw_text: str


@dataclass(frozen=True)
class ContributorRecord:
    """One contributor entry, preserved as found.

    Attributes:
        contrib_type: The source ``contrib-type`` value, exactly as
            written (e.g. ``"author"``, ``"editor"``) — used only to sort
            into :attr:`ContributorMetadata.authors` /
            :attr:`~ContributorMetadata.editors` /
            :attr:`~ContributorMetadata.other_contributors`, never
            reclassified.
        surname: The surname text, if present.
        given_names: The given-names text, if present.
        orcid: The ORCID value, if present, exactly as written.
        emails: Every email value found for this contributor, in document
            order.
        affiliation_ref_ids: Every affiliation id this contributor
            references, in document order.
        is_corresponding: Whether a corresponding-author indicator was
            found (a ``corresp="yes"``-style attribute, or a
            ``ref-type="corresp"`` cross-reference) — a structural
            detection, not a business judgment about who to contact.
        suffix: The ``name/suffix`` text (e.g. ``"PhD"``), if present.
            Added in Milestone 5C — confirmed present in real reference
            package data.
        equal_contrib: Whether the source ``equal-contrib="yes"``
            attribute was found on this contributor. Added in Milestone
            5C — confirmed present in real reference package data.
        is_submitting_author: Whether the source ``data-submitting-author="yes"``
            attribute was found on this contributor — a structural
            detection, not a business judgment about who submitted.
    """

    contrib_type: str | None
    surname: str | None
    given_names: str | None
    orcid: str | None
    emails: tuple[str, ...] = field(default_factory=tuple)
    affiliation_ref_ids: tuple[str, ...] = field(default_factory=tuple)
    is_corresponding: bool = False
    suffix: str | None = None
    equal_contrib: bool = False
    is_submitting_author: bool = False


@dataclass(frozen=True)
class ContributorMetadata:
    """Contributor-level metadata extracted from a parsed document.

    Attributes:
        authors: Every contributor whose ``contrib_type`` indicates an
            author, in document order.
        editors: Every contributor whose ``contrib_type`` indicates an
            editor, in document order.
        other_contributors: Every other contributor entry, in document
            order.
        affiliations: Every affiliation entry found, in document order.
    """

    authors: tuple[ContributorRecord, ...] = field(default_factory=tuple)
    editors: tuple[ContributorRecord, ...] = field(default_factory=tuple)
    other_contributors: tuple[ContributorRecord, ...] = field(default_factory=tuple)
    affiliations: tuple[AffiliationRecord, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class JournalMetadata:
    """Journal-level metadata extracted from a parsed document.

    Attributes:
        journal_title: The journal title text, if found.
        journal_id: The verbatim ``journal-id[@journal-id-type=publisher-id]``
            text, exactly as written (not lower-cased — that ADR-028
            config-lookup-key normalization is a Milestone 5B transform
            concern, not an extraction-layer one). Added in Milestone 5B
            (Metadata → ICAM Transformation) as a small, additive
            extension of this already-approved Milestone 4 type — see the
            Milestone 5B Architecture Compliance Report.
        issns: Every ISSN value found, paired with its source
            ``pub-type`` (e.g. ``"ppub"``, ``"epub"``), in document order.
        publisher_name: The publisher name text, if found.
        volume: The volume text, if found.
        issue: The issue text, if found.
        fpage: The first-page text, if found.
        lpage: The last-page text, if found.
        elocation_id: The e-location id text, if found.
        doi_related_ids: DOI-typed identifier values, duplicated here
            from :attr:`ArticleMetadata.identifiers` as a convenience
            grouping only — this is not a second extraction pass, see the
            Milestone 4 Architecture Compliance Report.
        abbrev_titles: Every ``abbrev-journal-title`` value found, paired
            with its source ``abbrev-type`` (e.g. ``"pubmed"``,
            ``"publisher"``), in document order. Added in Milestone 5B,
            same rationale as ``journal_id``.
        journal_ids: Every ``journal-id`` value found, paired with its
            source ``journal-id-type`` (e.g. ``"publisher-id"``,
            ``"nlm-ta"``), in document order — ``journal_id`` above only
            ever captured the first ``publisher-id`` match (needed for
            ADR-028 config lookup); this preserves every type present
            (Milestone 9 journal-metadata completeness correction), the
            same pattern as ``abbrev_titles``.
    """

    journal_title: str | None = None
    journal_id: str | None = None
    issns: tuple[tuple[str | None, str], ...] = field(default_factory=tuple)
    publisher_name: str | None = None
    abbrev_titles: tuple[tuple[str | None, str], ...] = field(default_factory=tuple)
    journal_ids: tuple[tuple[str | None, str], ...] = field(default_factory=tuple)
    volume: str | None = None
    issue: str | None = None
    fpage: str | None = None
    lpage: str | None = None
    elocation_id: str | None = None
    doi_related_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WorkflowEventRecord:
    """One workflow/log event, flattened but not interpreted.

    Attributes:
        event_tag: The source element's local tag name.
        fields: Every direct simple-text child's (tag, text) pair, in
            document order — no timeline reconstruction, no event-type
            classification.
        raw_element: The original parsed element, for full-fidelity
            fallback access.
    """

    event_tag: str
    fields: tuple[tuple[str, str], ...]
    raw_element: ParsedElement


@dataclass(frozen=True)
class WorkflowMetadata:
    """Workflow-level metadata extracted from a parsed document.

    Attributes:
        events: Every workflow/log event found, in document order.
    """

    events: tuple[WorkflowEventRecord, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class NamedContentField:
    """One ``named-content``-style sub-value found inside a custom-meta entry.

    Attributes:
        content_type: The source content-type value, exactly as written.
        text: The text content.
    """

    content_type: str | None
    text: str


@dataclass(frozen=True)
class CustomMetaEntry:
    """One custom-metadata entry, preserved unfiltered.

    Attributes:
        name: The entry's name/key text, if present.
        value_text: The entry's flattened value text.
        named_content: Every named-content sub-value found within this
            entry's value, in document order.
        attributes: Every attribute on the ``<custom-meta>`` element
            itself (e.g. ``specific-use``, ``data-version``,
            ``data-reviewer-email``, ``data-user-role``), verbatim,
            in document order. Added in Milestone 5B (Metadata → ICAM
            Transformation): real reference-package data showed these
            attributes — not the ``meta-name``/``meta-value`` content —
            carry the round/reviewer/actor/timestamp signals
            :mod:`meca_engine.extraction.custom_meta_classifier` needs
            to classify an entry, and roughly two-thirds of one real
            sample's entries have no ``meta-name`` at all. A generic,
            open-ended ``attributes`` field (rather than named fields
            per observed attribute) matches BR-019's "category vocabulary
            is open" philosophy and this codebase's established
            preserve-everything-verbatim convention.
    """

    name: str | None
    value_text: str
    named_content: tuple[NamedContentField, ...] = field(default_factory=tuple)
    attributes: tuple[tuple[str, str], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CustomMetadata:
    """Custom-metadata extracted from a parsed document.

    Attributes:
        entries: Every custom-meta entry found, unfiltered and
            unclassified, in document order. Business-rule-driven
            filtering (the deny-list logic) is deferred to a later
            milestone's classifier, built on top of this extraction.
    """

    entries: tuple[CustomMetaEntry, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AssetRecord:
    """One structural asset entry (figure, table, supplementary file, etc.).

    Attributes:
        asset_tag: The source element's local tag name (e.g. ``"fig"``,
            ``"table-wrap"``) — a schema-level fact, not a business
            classification.
        element_id: The asset element's own id, if present.
        label: The asset's label text, if present.
        file_references: Every structural file reference found within
            this asset's subtree, in document order.
    """

    asset_tag: str
    element_id: str | None
    label: str | None
    file_references: tuple[FileReference, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AssetMetadata:
    """Asset metadata extracted from a parsed document.

    Attributes:
        assets: Every recognized asset entry found, in document order.
    """

    assets: tuple[AssetRecord, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReferenceRecord:
    """One cross-reference from an element to one or more target ids.

    Attributes:
        referencing_tag: The local tag name of the element carrying the
            reference attribute.
        referencing_ref_type: The source ``ref-type`` value on the
            referencing element, if present, exactly as written.
        attribute_name: The reference attribute's local name.
        target_ids: Every id token the reference attribute's value
            resolves to (whitespace-separated), in order — whether or not
            each one was actually found in the document's id index (that
            check is a diagnostic, not a filter here).
    """

    referencing_tag: str
    referencing_ref_type: str | None
    attribute_name: str
    target_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CrossReferenceMap:
    """Cross-reference relationships extracted from a parsed document.

    Attributes:
        id_index: A compact mapping from id value to the tag name of the
            element carrying it (not the full element, to avoid
            duplicating the separate Parsed Object snapshot).
        references: Every cross-reference found, in document order.
    """

    id_index: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    references: tuple[ReferenceRecord, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ExtractionBundle:
    """The complete result of running every extractor over one parsed document.

    Attributes:
        article: Article-level metadata.
        contributors: Contributor-level metadata.
        journal: Journal-level metadata.
        workflow: Workflow-level metadata.
        custom: Custom metadata.
        assets: Asset metadata.
        cross_references: Cross-reference relationships.
        diagnostics: Every diagnostic raised by any extractor, combined,
            in extractor-then-document order.
    """

    article: ArticleMetadata
    contributors: ContributorMetadata
    journal: JournalMetadata
    workflow: WorkflowMetadata
    custom: CustomMetadata
    assets: AssetMetadata
    cross_references: CrossReferenceMap
    diagnostics: tuple[ParseDiagnostic, ...] = field(default_factory=tuple)
