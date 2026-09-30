"""RawXmlGenerator — Milestone 6B (11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.7).

Converts the frozen ICAM into raw.xml per Business Rule Book BR-036–050.
Every mapping function below is traceable to one or more BR numbers,
documented in its own docstring — see
`20_MILESTONE_6B_RAW_XML_GENERATOR_REPORT.md`'s field-mapping matrix for
the complete BR → module → test cross-reference.

**Confirmed, documented ICAM gaps** (not fixed here — out of this
milestone's scope; see the report's Architecture Compliance section for
the full evidence):

- BR-039 ("retains every source ``id``") — `ArticleMeta`/`Affiliation`/
  `Contributor`/`JournalMeta` deliberately never preserve source element
  ids (Milestone 5B's own documented reasoning: article.xml strips ids,
  so ICAM linkage was designed around model-internal keys instead). Only
  ``BodyFragment.raw_xml_fragment`` (a verbatim string copy) retains any
  ids, and only within ``<body>``.
- BR-042 ("100% of custom-meta-group, no pruning") — `CustomMetaStore` is
  `custom_meta_classifier`'s *classified* output, not the unfiltered
  Milestone 4 entries (which silently drops entries with no recognizable
  ``meta-name`` — see that module's own docstring). This generator
  reconstructs ``<custom-meta-group>`` from the classified store's own
  fields — the closest BR-042-shaped output achievable from what the
  ICAM actually carries, never a byte-identical copy.
- ``<journal-id journal-id-type="publisher-id">`` — the only ICAM field
  available, `ArticleIdentity.journal_id`, is ADR-028's **lower-cased**
  config-lookup key, not the verbatim source string (confirmed against
  real data: one sample's source is ``"CS"``, its ICAM value ``"cs"``).
- ``<back>`` (references, footnotes, supplementary-material) has no ICAM
  representation at all today — omitted, with a diagnostic recorded, not
  fabricated.
- No ICAM field carries ``<article-meta>``'s ``subtitle``, ``pub-date``,
  ``volume``/``issue``/``fpage``/``lpage``/``elocation-id`` (all
  extracted at Milestone 4 but never wired into any Milestone 5B/5C ICAM
  transformer) — each omitted with a diagnostic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.generators.base import BaseGenerator
from meca_engine.generators.raw_xml.document import RawXmlDocument
from meca_engine.generators.xml.builder import DoctypeDeclaration, XmlDocumentBuilder
from meca_engine.generators.xml.helpers import (
    add_custom_meta_entry,
    add_optional_element,
    format_year_month_day,
    parse_fragment_with_namespaces,
)

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from meca_engine.config.schema import RawXmlConfig
    from meca_engine.generators.context import GeneratorContext
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.xml.namespaces import NamespaceManager
    from meca_engine.model.article import (
        ArticleIdentity,
        ArticleMeta,
        Contributor,
        CustomMetaStore,
        HistoryDates,
        JournalMeta,
    )

_GENERATOR_NAME = "raw_xml"


class RawXmlGenerator(BaseGenerator[RawXmlDocument]):
    """Generates raw.xml from the ICAM. See module docstring for BR traceability."""

    def __init__(
        self, *, namespace_manager: NamespaceManager, raw_xml_config: RawXmlConfig
    ) -> None:
        """Initialize the generator.

        Args:
            namespace_manager: Resolves BR-037's 4 namespace prefixes.
            raw_xml_config: BR-036/38/40/44/49/50's externalized constants.
        """
        self._namespace_manager = namespace_manager
        self._config = raw_xml_config

    @property
    def generator_name(self) -> str:
        """This generator's stable name, ``"raw_xml"``."""
        return _GENERATOR_NAME

    @property
    def namespace_prefixes(self) -> tuple[str, ...]:
        """BR-037's namespace prefixes, unconditionally declared on this generator's root element.

        Exposed so a downstream generator that derives from raw.xml's
        already-serialized output (e.g. `ArticleXmlGenerator`, BR-051)
        can reparse it correctly without hard-coding a second,
        possibly-drifting copy of this same prefix set.
        """
        return self._config.namespace_prefixes

    def _generate(self, context: GeneratorContext) -> RawXmlDocument:
        model = context.model
        config = self._config
        builder = XmlDocumentBuilder()

        root_attributes = {
            **self._namespace_manager.declarations(config.namespace_prefixes),  # BR-037
            "article-type": config.article_type,  # BR-040
            "dtd-version": config.dtd_version,  # BR-049
            "xml:lang": config.default_xml_lang,  # BR-050
        }
        root = builder.create_root("article", attributes=root_attributes)

        front = builder.create_element(root, "front")
        _build_journal_meta(builder, front, model.journal_meta, model.identity, context.diagnostics)
        article_meta = builder.create_element(front, "article-meta")
        _build_article_meta(
            builder,
            article_meta,
            model.article_meta,
            model.identity,
            model.journal_meta,
            model.custom_meta,
            context.diagnostics,
        )

        _attach_body(
            root,
            model.body_fragment.raw_xml_fragment,
            context.diagnostics,
            self._namespace_manager,
            config.namespace_prefixes,
        )
        _diagnose_missing_back_matter(context.diagnostics)

        xml_bytes = builder.serialize(
            root,
            pretty=True,
            encoding=config.encoding,  # BR-038
            indent_spaces=config.pretty_indent_spaces,  # BR-044
            doctype=DoctypeDeclaration(  # BR-036
                root_tag="article",
                public_id=config.doctype_public_id,
                system_id=config.doctype_system_id,
            ),
        )

        return RawXmlDocument(
            article_id=model.identity.article_id,
            filename=f"{model.identity.article_id}_raw.xml",  # BR-048
            xml_bytes=xml_bytes,
        )


# --- front/journal-meta -------------------------------------------------------


def _build_journal_meta(
    builder: XmlDocumentBuilder,
    parent: Element,
    journal_meta: JournalMeta,
    identity: ArticleIdentity,
    diagnostics: DiagnosticsCollector,
) -> Element:
    element = builder.create_element(parent, "journal-meta")
    if identity.journal_id:
        # `ArticleIdentity.journal_id` is ADR-028's lower-cased config
        # lookup key, not necessarily the verbatim source string — see
        # the module docstring's documented gap.
        builder.create_element(
            element,
            "journal-id",
            attributes={"journal-id-type": "publisher-id"},
            text=identity.journal_id,
        )
    else:
        diagnostics.warn(_GENERATOR_NAME, "No journal-id available for journal-meta")

    for id_type, value in journal_meta.journal_ids:
        # The `publisher-id`-typed entry is already emitted above, sourced
        # from `identity.journal_id` (BR-058's DOI-derivation input) — every
        # other type (e.g. `nlm-ta`) was previously dropped entirely.
        if id_type == "publisher-id":
            continue
        builder.create_element(
            element, "journal-id", attributes={"journal-id-type": id_type}, text=value
        )

    title_group = builder.create_element(element, "journal-title-group")
    add_optional_element(builder, title_group, "journal-title", journal_meta.journal_title)
    for abbrev_type, value in journal_meta.abbrev_titles:
        builder.create_element(
            title_group, "abbrev-journal-title", attributes={"abbrev-type": abbrev_type}, text=value
        )

    if journal_meta.issn_ppub:
        builder.create_element(
            element, "issn", attributes={"pub-type": "ppub"}, text=journal_meta.issn_ppub
        )
    if journal_meta.issn_epub:
        builder.create_element(
            element, "issn", attributes={"pub-type": "epub"}, text=journal_meta.issn_epub
        )
    if not journal_meta.issn_ppub and not journal_meta.issn_epub:
        diagnostics.info(_GENERATOR_NAME, "No ISSN available for journal-meta")

    publisher = builder.create_element(element, "publisher")
    add_optional_element(builder, publisher, "publisher-name", journal_meta.publisher_name)
    return element


# --- front/article-meta --------------------------------------------------------


def _build_article_meta(
    builder: XmlDocumentBuilder,
    parent: Element,
    article_meta: ArticleMeta,
    identity: ArticleIdentity,
    journal_meta: JournalMeta,
    custom_meta: CustomMetaStore,
    diagnostics: DiagnosticsCollector,
) -> None:
    _build_article_ids(builder, parent, identity, diagnostics)
    _build_article_categories(builder, parent, article_meta)
    _build_title_group(builder, parent, article_meta)
    _build_contrib_group(builder, parent, article_meta, diagnostics)
    _build_author_notes(builder, parent, article_meta, diagnostics)
    _build_publication_info(builder, parent, article_meta, journal_meta)
    _build_history(builder, parent, article_meta.history_dates, diagnostics)
    _build_permissions(builder, parent, article_meta, diagnostics)
    _build_abstracts(builder, parent, article_meta, diagnostics)
    _build_kwd_group(builder, parent, article_meta, diagnostics)
    _build_funding_group(builder, parent, article_meta, diagnostics)
    _build_counts(builder, parent, article_meta, diagnostics)
    _build_custom_meta_group(builder, parent, custom_meta, diagnostics)


def _build_article_ids(
    builder: XmlDocumentBuilder,
    parent: Element,
    identity: ArticleIdentity,
    diagnostics: DiagnosticsCollector,
) -> None:
    """BR-039 (verbatim article-id values, `ArticleIdentity`'s own source fields)."""
    if identity.publisher_id_value:
        builder.create_element(
            parent,
            "article-id",
            attributes={"pub-id-type": "publisher-id"},
            text=identity.publisher_id_value,
        )
    else:
        diagnostics.warn(_GENERATOR_NAME, "No publisher-id article-id available")
    if identity.doi_article_id_value:
        builder.create_element(
            parent,
            "article-id",
            attributes={"pub-id-type": "doi"},
            text=identity.doi_article_id_value,
        )
    else:
        diagnostics.info(_GENERATOR_NAME, "No doi article-id available")


def _build_article_categories(
    builder: XmlDocumentBuilder, parent: Element, article_meta: ArticleMeta
) -> None:
    """Copies `display_channel_subject`/`heading_subjects` verbatim.

    Same "no transformation" spirit as BR-043's body copy.
    """
    if not article_meta.display_channel_subject and not article_meta.heading_subjects:
        return
    categories = builder.create_element(parent, "article-categories")
    if article_meta.display_channel_subject:
        display = builder.create_element(
            categories, "subj-group", attributes={"subj-group-type": "display-channel"}
        )
        builder.create_element(display, "subject", text=article_meta.display_channel_subject)
    for heading in article_meta.heading_subjects:
        heading_group = builder.create_element(
            categories, "subj-group", attributes={"subj-group-type": "heading"}
        )
        builder.create_element(heading_group, "subject", text=heading)


def _build_title_group(
    builder: XmlDocumentBuilder, parent: Element, article_meta: ArticleMeta
) -> None:
    """BR-043-consistent verbatim title copy. No ICAM `subtitle` field exists (documented gap)."""
    title_group = builder.create_element(parent, "title-group")
    builder.create_element(title_group, "article-title", text=article_meta.article_title)


def _build_contrib_group(
    builder: XmlDocumentBuilder,
    parent: Element,
    article_meta: ArticleMeta,
    diagnostics: DiagnosticsCollector,
) -> None:
    """Renders every affiliation, then one `<contrib-group>` for every `Contributor`.

    Source raw.xml has multiple ``contrib-group`` elements, one per role
    grouping (author/editor/associate-editor/reviewer/copyediting) —
    `ArticleMeta.contributors` is a single, already-flattened list (see
    `contributor_transformer`'s module docstring), so this generator
    emits one `<contrib-group>` covering all of them, preserving each
    contributor's own `contrib_type` on its `<contrib>` element rather
    than re-deriving the source's multi-group structure (not available
    in the ICAM).
    """
    if not article_meta.affiliations:
        diagnostics.info(_GENERATOR_NAME, "No affiliations available")
    for affiliation in article_meta.affiliations:
        aff = builder.create_element(
            parent, "aff", attributes={"id": f"aff{affiliation.model_key}"}
        )
        add_optional_element(builder, aff, "label", affiliation.label)
        add_optional_element(builder, aff, "institution", affiliation.institution)
        add_optional_element(
            builder, aff, "addr-line", affiliation.city, attributes={"content-type": "city"}
        )
        add_optional_element(
            builder, aff, "addr-line", affiliation.state, attributes={"content-type": "state"}
        )
        add_optional_element(builder, aff, "country", affiliation.country)

    if not article_meta.contributors:
        diagnostics.warn(_GENERATOR_NAME, "No contributors available")
        return

    contrib_group = builder.create_element(parent, "contrib-group")
    for contributor in article_meta.contributors:
        _build_contrib(builder, contrib_group, contributor)


def _build_contrib(
    builder: XmlDocumentBuilder, parent: Element, contributor: Contributor
) -> Element:
    """BR-039-style verbatim role preservation via `raw_contrib_type` where available."""
    contrib_type = contributor.raw_contrib_type or contributor.contrib_type.value
    attributes = {"contrib-type": contrib_type}
    if contributor.is_corresponding:
        attributes["corresp"] = "yes"
    if contributor.equal_contrib:
        attributes["equal-contrib"] = "yes"
    contrib = builder.create_element(parent, "contrib", attributes=attributes)

    if contributor.full_name_raw:
        builder.create_element(contrib, "string-name", text=contributor.full_name_raw)
    else:
        name = builder.create_element(contrib, "name")
        builder.create_element(name, "surname", text=contributor.surname)
        builder.create_element(name, "given-names", text=contributor.given_names)
        add_optional_element(builder, name, "suffix", contributor.suffix)

    if contributor.orcid:
        builder.create_element(
            contrib, "contrib-id", attributes={"contrib-id-type": "orcid"}, text=contributor.orcid
        )
    add_optional_element(builder, contrib, "email", contributor.email)
    for key in contributor.affiliation_keys:
        builder.create_element(
            contrib, "xref", attributes={"ref-type": "aff", "rid": f"aff{key}"}, text=str(key)
        )
    return contrib


def _build_author_notes(
    builder: XmlDocumentBuilder,
    parent: Element,
    article_meta: ArticleMeta,
    diagnostics: DiagnosticsCollector,
) -> None:
    """BR-039-style structural mapping of `ArticleMeta.corresponding_emails`.

    Only the email is available (`CorrespEmail` carries no contributor
    name) — the source's ``<corresp>Name, <email>...`` text prefix is
    not reproduced; see the module docstring's documented gap.
    """
    if not article_meta.corresponding_emails:
        diagnostics.info(_GENERATOR_NAME, "No corresponding-author email available")
        return
    author_notes = builder.create_element(parent, "author-notes")
    for index, corresp_email in enumerate(article_meta.corresponding_emails, start=1):
        corresp = builder.create_element(author_notes, "corresp", attributes={"id": f"cor{index}"})
        builder.create_element(
            corresp,
            "email",
            attributes={"xlink:href": corresp_email.email, "xlink:type": "simple"},
            text=corresp_email.email,
        )


def _build_publication_info(
    builder: XmlDocumentBuilder,
    parent: Element,
    article_meta: ArticleMeta,
    journal_meta: JournalMeta,
) -> None:
    """Milestone 9 addition: pub-date/volume/issue/fpage/lpage, previously never emitted.

    Extracted since Milestone 4/5B but never wired past the transform
    layer — see `journal_transformer`'s and `coordinator`'s own
    correction notes.
    """
    for pub_type, value in article_meta.pub_dates:
        pub_date = builder.create_element(parent, "pub-date", attributes={"pub-type": pub_type})
        year, month, day = format_year_month_day(value)
        builder.create_element(pub_date, "day", text=day)
        builder.create_element(pub_date, "month", text=month)
        builder.create_element(pub_date, "year", text=year)
    add_optional_element(builder, parent, "volume", journal_meta.volume)
    add_optional_element(builder, parent, "issue", journal_meta.issue)
    add_optional_element(builder, parent, "fpage", journal_meta.fpage)
    add_optional_element(builder, parent, "lpage", journal_meta.lpage)


def _build_history(
    builder: XmlDocumentBuilder,
    parent: Element,
    history_dates: HistoryDates,
    diagnostics: DiagnosticsCollector,
) -> None:
    """BR-047: `history` dates copied verbatim from `ArticleMeta.history_dates`."""
    dates = [
        (date_type, value)
        for date_type, value in (
            ("received", history_dates.received),
            ("revised", history_dates.revision),
            ("accepted", history_dates.accepted),
        )
        if value is not None
    ]
    if not dates:
        diagnostics.info(_GENERATOR_NAME, "No history dates available")
        return
    history = builder.create_element(parent, "history")
    for date_type, value in dates:
        date_element = builder.create_element(history, "date", attributes={"date-type": date_type})
        year, month, day = format_year_month_day(value)
        builder.create_element(date_element, "day", text=day)
        builder.create_element(date_element, "month", text=month)
        builder.create_element(date_element, "year", text=year)


def _build_permissions(
    builder: XmlDocumentBuilder,
    parent: Element,
    article_meta: ArticleMeta,
    diagnostics: DiagnosticsCollector,
) -> None:
    """BR-045 (verbatim copyright wording); BR-046 (raw.xml never adds `<license>`)."""
    if not article_meta.copyright_statement and not article_meta.copyright_year:
        diagnostics.info(_GENERATOR_NAME, "No copyright/permissions information available")
        return
    permissions = builder.create_element(parent, "permissions")
    add_optional_element(
        builder, permissions, "copyright-statement", article_meta.copyright_statement
    )
    add_optional_element(builder, permissions, "copyright-year", article_meta.copyright_year)


def _build_abstracts(
    builder: XmlDocumentBuilder,
    parent: Element,
    article_meta: ArticleMeta,
    diagnostics: DiagnosticsCollector,
) -> None:
    if not article_meta.abstracts:
        diagnostics.warn(_GENERATOR_NAME, "No abstract available")
        return
    for abstract in article_meta.abstracts:
        attributes = {}
        if abstract.abstract_type:
            attributes["abstract-type"] = abstract.abstract_type
        if abstract.language:
            attributes["xml:lang"] = abstract.language
        element = builder.create_element(parent, "abstract", attributes=attributes or None)
        builder.create_element(element, "p", text=abstract.text)


def _build_kwd_group(
    builder: XmlDocumentBuilder,
    parent: Element,
    article_meta: ArticleMeta,
    diagnostics: DiagnosticsCollector,
) -> None:
    if not article_meta.keywords:
        diagnostics.info(_GENERATOR_NAME, "No keywords available")
        return
    kwd_group = builder.create_element(parent, "kwd-group")
    for keyword in article_meta.keywords:
        builder.create_element(kwd_group, "kwd", text=keyword)


def _build_funding_group(
    builder: XmlDocumentBuilder,
    parent: Element,
    article_meta: ArticleMeta,
    diagnostics: DiagnosticsCollector,
) -> None:
    if not article_meta.funding:
        diagnostics.info(_GENERATOR_NAME, "No funding information available")
        return
    for statement in article_meta.funding:
        builder.create_element(parent, "funding-group", text=statement)


def _build_counts(
    builder: XmlDocumentBuilder,
    parent: Element,
    article_meta: ArticleMeta,
    diagnostics: DiagnosticsCollector,
) -> None:
    counts_data = article_meta.counts
    ordered_counts = (
        ("fig-count", counts_data.fig_count),
        ("table-count", counts_data.table_count),
        ("equation-count", counts_data.equation_count),
        ("ref-count", counts_data.ref_count),
        ("page-count", counts_data.page_count),
        ("word-count", counts_data.word_count),
    )
    if all(value is None for _, value in ordered_counts):
        diagnostics.info(_GENERATOR_NAME, "No structural counts available")
        return
    counts = builder.create_element(parent, "counts")
    for tag, value in ordered_counts:
        if value is not None:
            builder.create_element(counts, tag, attributes={"count": str(value)})


# --- custom-meta-group (BR-042) -----------------------------------------------


def _build_custom_meta_group(
    builder: XmlDocumentBuilder,
    parent: Element,
    custom_meta: CustomMetaStore,
    diagnostics: DiagnosticsCollector,
) -> None:
    """Best-effort BR-042 reconstruction from the classified `CustomMetaStore`.

    Not a verbatim copy — see the module docstring's documented gap.
    Every classified collection is rendered as one or more
    ``<custom-meta><meta-name>.../<meta-value>...`` entries, in the
    order: form answers, file entries, reviewer scorecards, decision
    drafts, decline reasons.
    """
    has_any = (
        custom_meta.form_answers.entries
        or custom_meta.file_entries
        or custom_meta.reviewer_scorecards
        or custom_meta.decision_drafts
        or custom_meta.decline_reasons
    )
    if not has_any:
        diagnostics.warn(_GENERATOR_NAME, "No custom-meta information available to reconstruct")
        return

    group = builder.create_element(parent, "custom-meta-group")
    _add_form_answer_entries(builder, group, custom_meta)
    _add_file_entries(builder, group, custom_meta, diagnostics)
    _add_reviewer_scorecard_entries(builder, group, custom_meta, diagnostics)
    _add_decision_draft_entries(builder, group, custom_meta)
    _add_decline_reason_entries(builder, group, custom_meta, diagnostics)


def _add_form_answer_entries(
    builder: XmlDocumentBuilder, group: Element, custom_meta: CustomMetaStore
) -> None:
    for entry in custom_meta.form_answers.entries:
        for value in entry.values:
            add_custom_meta_entry(builder, group, entry.key, value)


def _add_file_entries(
    builder: XmlDocumentBuilder,
    group: Element,
    custom_meta: CustomMetaStore,
    diagnostics: DiagnosticsCollector,
) -> None:
    if not custom_meta.file_entries:
        diagnostics.info(_GENERATOR_NAME, "No file-manifest custom-meta entries available")
    for file_entry in custom_meta.file_entries:
        add_custom_meta_entry(
            builder,
            group,
            "file",
            f"{file_entry.category}: {file_entry.original_filename} ({file_entry.round_label})",
        )


def _add_reviewer_scorecard_entries(
    builder: XmlDocumentBuilder,
    group: Element,
    custom_meta: CustomMetaStore,
    diagnostics: DiagnosticsCollector,
) -> None:
    if not custom_meta.reviewer_scorecards:
        diagnostics.warn(_GENERATOR_NAME, "No reviewer scorecard custom-meta entries available")
    for scorecard in custom_meta.reviewer_scorecards:
        add_custom_meta_entry(
            builder,
            group,
            f"reviewer-scorecard:{scorecard.reviewer_name}",
            scorecard.overall_recommendation or "",
        )


def _add_decision_draft_entries(
    builder: XmlDocumentBuilder, group: Element, custom_meta: CustomMetaStore
) -> None:
    for draft in custom_meta.decision_drafts:
        add_custom_meta_entry(builder, group, "Decision Draft", draft.decision_text)


def _add_decline_reason_entries(
    builder: XmlDocumentBuilder,
    group: Element,
    custom_meta: CustomMetaStore,
    diagnostics: DiagnosticsCollector,
) -> None:
    if not custom_meta.decline_reasons:
        diagnostics.info(
            _GENERATOR_NAME, "No reviewer decline-reason custom-meta entries available"
        )
    for decline in custom_meta.decline_reasons:
        add_custom_meta_entry(builder, group, "reviewer-decline-reason", decline.reason_text)


# --- body (BR-043) -------------------------------------------------------------


def _attach_body(
    root: Element,
    raw_xml_fragment: str,
    diagnostics: DiagnosticsCollector,
    namespace_manager: NamespaceManager,
    namespace_prefixes: tuple[str, ...],
) -> None:
    """BR-043: `<body>` is a verbatim copy.

    Reparses `BodyFragment.raw_xml_fragment` (already-serialized, trusted
    ICAM text, never external input) back into a tree so it can be
    attached as a normal child element, rather than string-concatenated
    by hand. The fragment may itself carry namespace-prefixed tags/
    attributes (Milestone 6C's `body_fragment_builder` fix now preserves
    them, e.g. `xlink:href`) that resolve to nothing on their own — a
    bare fragment has no `xmlns:*` declarations in scope, so parsing goes
    through :func:`~meca_engine.generators.xml.helpers.parse_fragment_with_namespaces`
    (shared with :mod:`meca_engine.generators.article_xml.generator`,
    never duplicated), declaring BR-037's 4 namespaces via the same
    `NamespaceManager` the root element itself uses.
    """
    if not raw_xml_fragment:
        diagnostics.warn(_GENERATOR_NAME, "No body content available")
        return
    declarations = namespace_manager.declarations(namespace_prefixes)
    body_element = parse_fragment_with_namespaces(raw_xml_fragment, declarations)
    root.append(body_element)


def _diagnose_missing_back_matter(diagnostics: DiagnosticsCollector) -> None:
    """Record a diagnostic for the always-omitted `<back>` element.

    References, footnotes, and supplementary-material have no ICAM
    representation today (see module docstring) — always diagnosed,
    never fabricated.
    """
    diagnostics.warn(
        _GENERATOR_NAME,
        "No <back> matter (references/footnotes) generated — not represented in the ICAM",
    )
