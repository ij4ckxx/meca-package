"""ArticleXmlGenerator — Milestone 6C (11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.7).

Transforms raw.xml (never source XML directly — BR-051) into article.xml
per Business Rule Book BR-051–075. Every mapping/transformation function
below is traceable to one or more BR numbers, documented in its own
docstring — see `22_MILESTONE_6C_ARTICLE_XML_GENERATOR_REPORT.md`'s
Transformation Matrix and Business Transformation Decision Log for the
complete BR → module → test cross-reference and the reasoning behind
every business decision this generator makes.

**Composes `RawXmlGenerator`** (dependency injection, not inheritance):
`_generate` calls it first to get the already-approved raw.xml content,
then transforms that — never re-derives JATS content independently from
the ICAM, so raw.xml and article.xml can never drift apart on the
sections they share (BR-060). This mirrors 11_LLD_02's own stated
dependency ("consumes its output type, not its class").

**Confirmed, documented gaps and evidence-based decisions** (see the
report for full detail):

- BR-054 ("strips every id='uuid' attribute") is implemented as a
  UUID-*pattern* match, not a blanket ``id`` removal — semantic ids this
  pipeline itself assigns (``aff1``, ``cor1``) are load-bearing
  cross-reference targets and must survive; only Kriyadocs-internal UUID
  ids are stripped.
- BR-070 ("keeps only the final submission-decision value") is **not
  implemented** — direct evidence against CS-2025-6808 shows all 4
  round-by-round `"submission-decision"` values pass through unfiltered
  in the real article.xml, contradicting the rule's own stated behavior.
  Treated as a Business Rule Book inaccuracy; BR-071's deny-list
  philosophy (pass through unless explicitly denied) applies instead.
- The CC-BY license is synthesized whenever no "license type" custom-meta
  key exists at all (as well as when one explicitly says so) — evidence:
  cs-2025-8827 carries no such key yet still receives the identical
  license block in its real article.xml. Documented as an evidence-based
  default pending explicit business confirmation (BR-065).
- **Milestone 9 correction**: `pub-date`/`volume`/`issue`/`fpage`/
  `lpage`, the second (`nlm-ta`) `journal-id`, and
  `table-count`/`equation-count`/`page-count` are now wired through
  (previously extracted at Milestone 4/5B but never reached any
  generator — see `raw_xml/generator.py`'s `_build_publication_info`
  and `_build_counts`, both inherited here via the verbatim
  `contrib-group`/`aff`/`counts`/`journal-meta` copy). The
  `abbrev-journal-title[@abbrev-type=publisher]` acronym was already
  wired correctly — this docstring's prior claim that it was omitted
  was stale.
- Still genuinely not implementable: `<kwd-group kwd-group-type=
  "extractedFromManuscript">` — the real reference's keywords are
  manuscript-file-derived, a source this architecture never reads.
- Real article.xml's rich `author-notes` (CRediT contribution footnotes,
  data-availability, ethics, conflict-of-interest `<fn>` blocks) has no
  corresponding Business Rule Book entry (BR-051–075) at all — being
  added under a real-reference-confirmed shape (Milestone 9), see
  `raw_xml/generator.py`'s `_build_author_notes`.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, NamedTuple

from meca_engine.exceptions import MissingDoiError
from meca_engine.generators.article_xml.document import ArticleXmlDocument
from meca_engine.generators.base import BaseGenerator
from meca_engine.generators.xml.builder import DoctypeDeclaration, XmlDocumentBuilder
from meca_engine.generators.xml.helpers import (
    add_custom_meta_entry,
    add_optional_element,
    drop_duplicate_children_by_attribute,
    insert_after_tag,
    normalize_idrefs_separator,
    parse_document_with_namespaces,
    rename_attribute_on_tag,
    strip_attribute,
    strip_attribute_matching,
    strip_characters,
    uses_prefix,
)
from meca_engine.model.enums import ContribType

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from meca_engine.config.schema import (
        ArticleTypeMappingConfig,
        ArticleXmlConfig,
        LicenseTemplatesConfig,
        PublisherAbbreviationMappingConfig,
    )
    from meca_engine.generators.context import GeneratorContext
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.raw_xml.generator import RawXmlGenerator
    from meca_engine.generators.xml.namespaces import NamespaceManager
    from meca_engine.model.article import ArticleIdentity, CustomMetaStore
    from meca_engine.model.collections import ContributorList, RoundIndex

_GENERATOR_NAME = "article_xml"
_XLINK_STRIPPED_ATTRIBUTES = ("xlink:href", "xlink:type")

# BR-054: strips only Kriyadocs-internal UUID-formatted `id` values —
# never a semantic id this pipeline itself assigns (e.g. "aff1", "cor1"),
# which remains load-bearing for cross-reference linking.
_UUID_ID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


class ArticleXmlGenerator(BaseGenerator[ArticleXmlDocument]):
    """Generates article.xml from raw.xml. See module docstring for BR traceability."""

    def __init__(
        self,
        *,
        raw_xml_generator: RawXmlGenerator,
        namespace_manager: NamespaceManager,
        article_xml_config: ArticleXmlConfig,
        article_type_mapping: ArticleTypeMappingConfig,
        license_templates: LicenseTemplatesConfig,
        publisher_abbreviation_mapping: PublisherAbbreviationMappingConfig,
    ) -> None:
        """Initialize the generator.

        Args:
            raw_xml_generator: Produces the raw.xml this generator
                derives article.xml from (BR-051) — never bypassed.
            namespace_manager: Resolves BR-056's conditional ``xlink``
                namespace.
            article_xml_config: BR-052/53/74's externalized constants.
            article_type_mapping: BR-057's display-channel → article-type
                lookup (Milestone 5C's `config/article-type-mapping.yaml`).
            license_templates: BR-063/064's License Type → boilerplate
                lookup.
            publisher_abbreviation_mapping: BR-164's
                journal-id[@journal-id-type=publisher-id] → publisher
                abbreviation lookup (`config/publisher-abbreviation-mapping.yaml`).
        """
        self._raw_xml_generator = raw_xml_generator
        self._namespace_manager = namespace_manager
        self._config = article_xml_config
        self._article_type_mapping = article_type_mapping
        self._license_templates = license_templates
        self._publisher_abbreviation_mapping = publisher_abbreviation_mapping

    @property
    def generator_name(self) -> str:
        """This generator's stable name, ``"article_xml"``."""
        return _GENERATOR_NAME

    def _generate(self, context: GeneratorContext) -> ArticleXmlDocument:
        model = context.model
        config = self._config
        diagnostics = context.diagnostics

        raw_result = self._raw_xml_generator.generate(context)  # BR-051
        raw_declarations = self._namespace_manager.declarations(
            self._raw_xml_generator.namespace_prefixes
        )
        raw_root = parse_document_with_namespaces(raw_result.document.xml_bytes, raw_declarations)
        raw_front = raw_root.find("front")
        raw_article_meta = raw_root.find("front/article-meta")

        builder = XmlDocumentBuilder()
        article_type = self._article_type_mapping.mappings.get(
            model.article_meta.display_channel_subject,
            self._article_type_mapping.default_article_type,
        )  # BR-057
        root = builder.create_root(
            "article",
            attributes={
                "dtd-version": config.dtd_version,  # BR-074
                "article-type": article_type,
            },
        )

        front = builder.create_element(root, "front")
        if raw_front is not None:
            _copy_journal_meta(
                builder, front, raw_front, self._publisher_abbreviation_mapping, diagnostics
            )

        article_meta = builder.create_element(front, "article-meta")
        if raw_article_meta is not None:
            _build_article_meta(
                builder,
                article_meta,
                raw_article_meta,
                model.identity,
                model.custom_meta,
                model.rounds,
                model.article_meta.contributors,
                context.journal_config.doi_prefix,
                self._license_templates,
                diagnostics,
            )

        if uses_prefix(root, "xlink"):  # BR-055/056
            xlink_uri = self._namespace_manager.uri_for("xlink")
            if xlink_uri is not None:
                root.set("xmlns:xlink", xlink_uri)

        xml_bytes = builder.serialize(
            root,
            pretty=True,
            encoding=config.encoding,  # BR-053
            indent_spaces=config.pretty_indent_spaces,
            doctype=DoctypeDeclaration(  # BR-052
                root_tag="article",
                public_id=config.doctype_public_id,
                system_id=config.doctype_system_id,
            ),
        )

        return ArticleXmlDocument(
            article_id=model.identity.article_id,
            filename=f"{model.identity.article_id}_article.xml",  # BR-073
            xml_bytes=xml_bytes,
        )


# --- front/journal-meta (BR-060) ----------------------------------------------


def _copy_journal_meta(
    builder: XmlDocumentBuilder,
    front: Element,
    raw_front: Element,
    publisher_abbreviation_mapping: PublisherAbbreviationMappingConfig,
    diagnostics: DiagnosticsCollector,
) -> None:
    raw_journal_meta = raw_front.find("journal-meta")
    if raw_journal_meta is None:
        diagnostics.warn(_GENERATOR_NAME, "No journal-meta available to copy from raw.xml")
        return
    journal_meta = builder.import_subtree(raw_journal_meta)
    stripped_ids = [d.attrib["id"] for d in journal_meta.iter() if "id" in d.attrib]
    if stripped_ids:
        diagnostics.info(
            _GENERATOR_NAME,
            f"Stripped {len(stripped_ids)} internal id(s) from journal-meta "
            f"({stripped_ids!r}): never a cross-reference target in this "
            "pipeline's output, so any id here — well-formed or corrupted — "
            "is stripped unconditionally rather than only UUID-pattern matches.",
        )
    # DTD-compliance finding (cs-2025-5853_C): a corrupted/mangled internal
    # id here (non-hex characters in UUID positions, starting with a digit)
    # doesn't match `_UUID_ID_PATTERN` and fails XML's `Name` syntax,
    # invalidating the DTD. Confirmed corpus-wide that no journal-meta id
    # is ever a cross-reference target (unlike "aff"/"cor" ids in
    # article-meta) — BR-054's own intent ("strip internal noise ids")
    # applies unconditionally here, not just to well-formed UUIDs.
    strip_attribute(journal_meta, "id")  # BR-054
    front.append(journal_meta)
    _apply_publisher_abbreviation_rule(
        builder, journal_meta, publisher_abbreviation_mapping, diagnostics
    )


def _apply_publisher_abbreviation_rule(
    builder: XmlDocumentBuilder,
    journal_meta: Element,
    mapping: PublisherAbbreviationMappingConfig,
    diagnostics: DiagnosticsCollector,
) -> None:
    """BR-164: deterministically derive the publisher abbreviation from ``journal-id``.

    Some sources never provide
    ``<abbrev-journal-title abbrev-type="publisher">`` at all — but the
    publisher abbreviation is fully determined by
    ``journal-id[@journal-id-type="publisher-id"]`` (already emitted, in
    ``journal_meta``, by ``raw_xml``'s own generator from
    ``identity.journal_id``), via a fixed, closed lookup table
    (`config/publisher-abbreviation-mapping.yaml`) — never a guess. An
    unrecognized publisher-id leaves ``journal_meta`` completely
    unchanged; a pre-existing publisher abbreviation is never duplicated.

    The lookup is case-insensitive (real corpus evidence: e.g.
    `CS-2025-6808`'s own ``journal-id`` is ``"CS"``, not the usual
    lowercase ``"cs"``, even though both plainly identify the same
    journal) — this is not a guess, since the matched key is still one of
    the fixed, closed set the mapping declares; it mirrors the same
    case-normalization fix already applied to the analogous
    article-id-prefix lookup in `service/worker.py`.
    """
    title_group = journal_meta.find("journal-title-group")
    if title_group is None:
        return
    if title_group.find('abbrev-journal-title[@abbrev-type="publisher"]') is not None:
        return  # already present — never generate a duplicate

    publisher_id = journal_meta.findtext('journal-id[@journal-id-type="publisher-id"]')
    if not publisher_id:
        return  # nothing to key the lookup off; not this rule's concern

    abbreviation = mapping.mappings.get(publisher_id) or mapping.mappings.get(publisher_id.lower())
    if abbreviation is None:
        diagnostics.warn(
            _GENERATOR_NAME,
            f"BR-164: no publisher abbreviation mapping exists for publisher-id "
            f"{publisher_id!r} — left unchanged (Validation Only).",
        )
        return

    abbrev_element = builder.create_element(
        title_group,
        "abbrev-journal-title",
        attributes={"abbrev-type": "publisher"},
        text=abbreviation,
    )
    insert_after_tag(title_group, abbrev_element, "journal-title")
    diagnostics.info(
        _GENERATOR_NAME,
        f"BR-164: generated publisher abbreviation {abbreviation!r} for "
        f"publisher-id {publisher_id!r}.",
    )


# --- front/article-meta --------------------------------------------------------

# DTD-compliance finding (JATS-archivearticle1.dtd validation, corpus-wide):
# `<article-meta>`'s content model is strictly sequenced — e.g. "volume"
# must precede "fpage"/"lpage", and both must precede "history"; "abstract"
# must precede "kwd-group", which must precede "funding-group"/"counts".
# raw.xml's own document order does NOT reliably match this (it mirrors
# whatever order the source XML happened to use), so copying each tag
# verbatim "wherever it appears in raw.xml" produced a DTD-invalid
# article.xml for several real articles (bst-2025-3098_C, bst-2025-3107_C,
# bst-2025-3131, ebc-2025-3054_C confirmed) even though it worked by
# coincidence for others. This tuple is now also the emission order
# `_build_article_meta` uses — not just a membership test — so every
# article gets the DTD-mandated sequence regardless of raw.xml's own
# order. "contrib-group" is handled separately (its own clustering logic,
# interleavable with "aff" per the DTD) and is not part of this list.
#
# Split into "before" (article-categories, title-group — DTD-required
# ahead of the contrib-group/aff/author-notes slot) and "after" (every
# tag that comes once contrib-group/aff/author-notes are done) — kept as
# one tuple since every consumer of _COPIED_VERBATIM_TAGS_ORDER cares
# about the full membership/order, not the split point itself.
_ARTICLE_META_TAGS_BEFORE_CONTRIB = ("article-categories", "title-group")
_ARTICLE_META_TAGS_AFTER_CONTRIB = (
    "pub-date",
    "volume",
    "issue",
    "fpage",
    "lpage",
    "history",
    "abstract",
    "kwd-group",
    "funding-group",
    "counts",
)
_COPIED_VERBATIM_TAGS_ORDER = _ARTICLE_META_TAGS_BEFORE_CONTRIB + _ARTICLE_META_TAGS_AFTER_CONTRIB
_COPIED_VERBATIM_TAGS = frozenset(_COPIED_VERBATIM_TAGS_ORDER)


def _build_article_meta(
    builder: XmlDocumentBuilder,
    article_meta: Element,
    raw_article_meta: Element,
    identity: ArticleIdentity,
    custom_meta: CustomMetaStore,
    rounds: RoundIndex,
    contributors: ContributorList,
    doi_prefix: str,
    license_templates: LicenseTemplatesConfig,
    diagnostics: DiagnosticsCollector,
) -> None:
    _build_article_ids(builder, article_meta, identity, doi_prefix, diagnostics)

    # Manual-verification finding (bcj-2025-3130): raw.xml can carry more
    # than one "contrib-group" (author/editor/associate-editor/reviewer/
    # suggested-reviewer), and a publisher's editorial-workflow export
    # doesn't always keep them adjacent — one straggler can land after
    # "abstract". Both real reference packages (Output/*.zip) cluster
    # every contrib-group together, right after "title-group", before
    # anything else.
    buckets = _bucket_article_meta_children(raw_article_meta)

    # DTD order: article-categories? , title-group? , THEN contrib-group/aff.
    for tag in _ARTICLE_META_TAGS_BEFORE_CONTRIB:
        for child in buckets.generic_by_tag[tag]:
            _append_copied(builder, article_meta, child)

    for group in buckets.contrib_groups:
        _append_copied(builder, article_meta, group)
    _build_submitting_author_contrib_group(builder, article_meta, contributors)

    # DTD slot: "(contrib-group | aff | aff-alternatives | x)*" — aff shares
    # contrib-group's own repeatable slot (any interleaving is DTD-valid),
    # right after title-group and before author-notes.
    for aff in buckets.aff_elements:
        _append_copied(builder, article_meta, aff)

    if buckets.author_notes:
        _copy_author_notes(builder, article_meta, buckets.author_notes, diagnostics)

    # DTD-compliance finding: `<article-meta>`'s content model is strictly
    # sequenced (e.g. "volume" before "fpage"/"lpage" before "history";
    # "abstract" before "kwd-group" before "funding-group"/"counts").
    # raw.xml's own document order does NOT reliably match this (it
    # mirrors whatever order the source XML happened to use), so copying
    # each tag verbatim "wherever it appears in raw.xml" produced a
    # DTD-invalid article.xml for several real articles (bst-2025-3098_C,
    # bst-2025-3107_C, bst-2025-3131, ebc-2025-3054_C confirmed) even
    # though it worked by coincidence for others. Emitting from
    # `_COPIED_VERBATIM_TAGS_ORDER` (not raw.xml's order) fixes this for
    # every article, not just the ones already known to fail.
    for tag in _ARTICLE_META_TAGS_AFTER_CONTRIB:
        for child in buckets.generic_by_tag[tag]:
            _append_copied(builder, article_meta, child)
        if tag == "history" and buckets.permissions is not None:
            # DTD position: ... , history? , pub-history? , permissions? ,
            # self-uri* , ... , abstract* — right after "history". Emitted
            # here (not inline in the loop above) since "permissions" needs
            # `_copy_permissions`, not a plain verbatim copy.
            _copy_permissions(
                builder,
                article_meta,
                buckets.permissions,
                custom_meta,
                license_templates,
                diagnostics,
            )

    _drop_duplicate_empty_aff_stubs(article_meta, diagnostics)
    _apply_spec_alignment_rules(article_meta, diagnostics)
    _build_custom_meta_group(builder, article_meta, custom_meta, rounds, diagnostics)


def _append_copied(builder: XmlDocumentBuilder, parent: Element, source: Element) -> None:
    """Import ``source`` as a subtree of ``parent``, with UUID ``id``s stripped (BR-054)."""
    copied = builder.import_subtree(source)
    strip_attribute_matching(copied, "id", _UUID_ID_PATTERN)
    parent.append(copied)


def _is_empty_aff_stub(aff: Element) -> bool:
    """True if ``aff`` carries no institution/address data beyond an optional ``label``."""
    return all(child.tag == "label" for child in aff) and not (aff.text or "").strip()


def _drop_duplicate_empty_aff_stubs(
    article_meta: Element, diagnostics: DiagnosticsCollector
) -> None:
    """Remove content-free ``aff`` elements that repeat an already-used id, anywhere in the tree.

    DTD-compliance finding (spec-alignment milestone, corpus-wide): 16/37
    articles carry a second ``<aff>`` sharing an already-used id (an XML ID
    must be document-unique) — confirmed in every case to be nested inside
    a per-contributor ``<contrib-group>`` (a source authoring-tool
    artifact), not a top-level article-meta sibling, so this walks the
    whole already-built tree rather than only article-meta's direct
    children. 9/16 are a content-free stub (just a repeated ``<label>``,
    e.g. ``<aff id="aff1"><label>1</label></aff>``, no institution/address
    at all) and are safe to drop — the first "aff1" already carries the
    full address, so nothing is lost. The other 7 (e.g. bst-2025-3127)
    carry a genuinely *different* institution's address under the same
    duplicate id — dropping either one would silently delete a real
    affiliation, so those are deliberately left as-is (a confirmed Source
    Data Issue, not auto-fixed — see Proposed_Recovery_Rules.md).
    """
    seen_ids: set[str] = set()
    to_remove: list[tuple[Element, Element, str]] = []
    for parent in article_meta.iter():
        for child in parent:
            if child.tag != "aff":
                continue
            aff_id = child.get("id")
            if aff_id is None:
                continue
            if aff_id not in seen_ids:
                seen_ids.add(aff_id)
            elif _is_empty_aff_stub(child):
                to_remove.append((parent, child, aff_id))

    for parent, child, aff_id in to_remove:
        parent.remove(child)
        diagnostics.info(
            _GENERATOR_NAME,
            f"Dropped duplicate empty aff stub (id={aff_id!r}): no institution "
            "data beyond a repeated label; the first aff with this id already "
            "carries the full address.",
        )


def _apply_spec_alignment_rules(article_meta: Element, diagnostics: DiagnosticsCollector) -> None:
    """Apply BR-161/162 (Business Rule Completion milestone) to the assembled tree.

    Both are deterministic, corpus-wide, lossless structural
    transformations — no value is invented, reinterpreted, or dropped;
    see `01_BUSINESS_RULE_BOOK.md` §K for the full rationale/evidence.
    """
    renamed = rename_attribute_on_tag(article_meta, "p", "data-type", "content-type")
    if renamed:
        diagnostics.info(
            _GENERATOR_NAME,
            f"BR-161: renamed data-type to content-type on {renamed} <p> element(s).",
        )

    normalized = normalize_idrefs_separator(article_meta, "xref", "rid")
    if normalized:
        diagnostics.info(
            _GENERATOR_NAME,
            f"BR-162: normalized comma-separated xref/@rid to whitespace on "
            f"{normalized} element(s).",
        )


class _ArticleMetaBuckets(NamedTuple):
    contrib_groups: list[Element]
    aff_elements: list[Element]
    generic_by_tag: dict[str, list[Element]]
    author_notes: list[Element]
    permissions: Element | None


def _bucket_article_meta_children(raw_article_meta: Element) -> _ArticleMetaBuckets:
    """Group ``raw_article_meta``'s children by tag, in their own relative order.

    A single pass so ``_build_article_meta`` can emit every tag in a fixed,
    DTD-mandated sequence afterwards instead of raw.xml's own order.
    """
    contrib_groups: list[Element] = []
    aff_elements: list[Element] = []
    generic_by_tag: dict[str, list[Element]] = {tag: [] for tag in _COPIED_VERBATIM_TAGS_ORDER}
    author_notes: list[Element] = []
    permissions: Element | None = None

    for child in raw_article_meta:
        if child.tag == "contrib-group":
            contrib_groups.append(child)
        elif child.tag == "aff":
            aff_elements.append(child)
        elif child.tag in _COPIED_VERBATIM_TAGS:
            generic_by_tag[child.tag].append(child)
        elif child.tag == "author-notes":
            # DTD-compliance finding (business-rule-completion milestone,
            # cs-2024-5002): article-meta's content model allows exactly
            # one `author-notes` (`author-notes?`), but some source
            # exports emit one separate `author-notes` wrapper PER
            # footnote instead of one wrapper containing every `fn`.
            # Every block found is kept (not just the last) — merged
            # into one DTD-valid wrapper by `_copy_author_notes` below.
            author_notes.append(child)
        elif child.tag == "permissions":
            permissions = child
        # "article-id"/"custom-meta-group" are handled elsewhere, never
        # matched here.

    return _ArticleMetaBuckets(
        contrib_groups, aff_elements, generic_by_tag, author_notes, permissions
    )


def _build_submitting_author_contrib_group(
    builder: XmlDocumentBuilder, article_meta: Element, contributors: ContributorList
) -> None:
    """Emit a ``contrib-group`` for whichever author the source explicitly flagged.

    Only ever built from ``data-submitting-author="yes"`` (surfaced as
    :attr:`~meca_engine.model.article.Contributor.is_submitting_author`) —
    never inferred or defaulted. If the source doesn't mark one, this
    does nothing, per this milestone's explicit "no fabrication" rule.
    """
    submitting_authors = [
        c for c in contributors if c.contrib_type is ContribType.AUTHOR and c.is_submitting_author
    ]
    if not submitting_authors:
        return

    group = builder.create_element(article_meta, "contrib-group")
    for author in submitting_authors:
        contrib = builder.create_element(
            group, "contrib", attributes={"contrib-type": "submitting-author"}
        )
        name = builder.create_element(contrib, "name")
        add_optional_element(builder, name, "surname", author.surname)
        add_optional_element(builder, name, "given-names", author.given_names)
        add_optional_element(builder, contrib, "email", author.email)


def _build_article_ids(
    builder: XmlDocumentBuilder,
    article_meta: Element,
    identity: ArticleIdentity,
    doi_prefix: str,
    diagnostics: DiagnosticsCollector,
) -> None:
    if identity.publisher_id_value:
        builder.create_element(
            article_meta,
            "article-id",
            attributes={"pub-id-type": "publisher-id"},
            text=identity.publisher_id_value,
        )
    else:
        diagnostics.warn(_GENERATOR_NAME, "No publisher-id article-id available")

    doi = _build_doi(identity.doi_article_id_value, doi_prefix)  # BR-058/059
    builder.create_element(article_meta, "article-id", attributes={"pub-id-type": "doi"}, text=doi)


def _build_doi(doi_article_id_value: str, doi_prefix: str) -> str:
    """BR-058: ``doi_prefix + "/" + doi_article_id`` with ``-``/``_`` stripped, casing preserved."""
    if not doi_article_id_value:
        raise MissingDoiError(
            "Cannot generate a DOI: no source doi article-id available",
            stage=_GENERATOR_NAME,
        )
    return f"{doi_prefix}/{strip_characters(doi_article_id_value, '-_')}"


def _copy_author_notes(
    builder: XmlDocumentBuilder,
    article_meta: Element,
    raw_author_notes_blocks: list[Element],
    diagnostics: DiagnosticsCollector,
) -> None:
    """BR-060 (copy, ids stripped) + BR-061 (strip xlink:href/type from corresp/email).

    DTD-compliance finding (bcj-2025-3130): the source export re-emits
    the same CRediT-role ``<fn>`` block multiple times under
    ``author-notes`` (same semantic id, e.g. "con2", same text each
    time) — raw.xml, in turn, already carries the same repeated ``id``
    literally. XML IDs must be document-unique, so copying every
    repeat verbatim produces a DTD-invalid article.xml. No information
    is lost by keeping only the first of each repeated id: all repeats
    are byte-identical (verified, not assumed — see
    ``drop_duplicate_children_by_attribute``).

    DTD-compliance finding (production-stabilization milestone,
    cs-2024-5002): ``article-meta`` allows only one ``author-notes``
    (``author-notes?``), but some sources emit a separate wrapper per
    footnote instead of one wrapper containing every ``fn``. Every
    block's children are copied here, in source order, into a single
    merged wrapper — no note is dropped, reordered, or combined with
    another; only an exact repeat is ever removed.
    """
    merged = builder.import_subtree(raw_author_notes_blocks[0])
    strip_attribute_matching(merged, "id", _UUID_ID_PATTERN)
    for extra_block in raw_author_notes_blocks[1:]:
        imported = builder.import_subtree(extra_block)
        strip_attribute_matching(imported, "id", _UUID_ID_PATTERN)
        for child in list(imported):
            merged.append(child)

    if len(raw_author_notes_blocks) > 1:
        diagnostics.info(
            _GENERATOR_NAME,
            f"Merged {len(raw_author_notes_blocks)} separate author-notes blocks "
            "from source into one wrapper (article-meta permits only one) — "
            "every note's content, order, and id was preserved.",
        )

    dropped_fn_ids = drop_duplicate_children_by_attribute(merged, "id")
    for fn_id in dropped_fn_ids:
        diagnostics.info(
            _GENERATOR_NAME,
            f"Dropped duplicate author-notes entry (id={fn_id!r}): byte-identical "
            "repeat already emitted once; the source re-exports the same "
            "CRediT-role footnote multiple times under this id.",
        )
    for corresp in merged.findall("corresp"):
        email = corresp.find("email")
        if email is not None:
            for attribute_name in _XLINK_STRIPPED_ATTRIBUTES:
                email.attrib.pop(attribute_name, None)
    article_meta.append(merged)


def _copy_permissions(
    builder: XmlDocumentBuilder,
    article_meta: Element,
    raw_permissions: Element,
    custom_meta: CustomMetaStore,
    license_templates: LicenseTemplatesConfig,
    diagnostics: DiagnosticsCollector,
) -> None:
    """BR-062 (copyright verbatim) + BR-063/064 (synthesized CC-BY license)."""
    permissions = builder.create_element(article_meta, "permissions")
    add_optional_element(
        builder, permissions, "copyright-statement", raw_permissions.findtext("copyright-statement")
    )
    add_optional_element(
        builder, permissions, "copyright-year", raw_permissions.findtext("copyright-year")
    )
    _add_license(builder, permissions, custom_meta, license_templates, diagnostics)


def _add_license(
    builder: XmlDocumentBuilder,
    permissions: Element,
    custom_meta: CustomMetaStore,
    license_templates: LicenseTemplatesConfig,
    diagnostics: DiagnosticsCollector,
) -> None:
    license_type = _resolve_license_type(custom_meta)
    if license_type is None:
        diagnostics.info(_GENERATOR_NAME, "No license synthesized: License Type is not CC-BY")
        return
    template = license_templates.templates.get(license_type)
    if template is None:
        # Milestone 11 (Recovery + Warning framework): a recognized but
        # unmapped License Type is a configuration gap (the templates
        # config is incomplete), not a reason to discard an otherwise
        # complete package — recover the same way an unrecognized/non-CC-BY
        # License Type already does just above: omit the <license>
        # element, keep everything else, warn instead of raising.
        diagnostics.warn(
            _GENERATOR_NAME,
            f"No license template configured for License Type {license_type!r}; "
            "license block omitted (recoverable, BR-063, RR-007)",
            context={"license_type": license_type},
        )
        return
    license_element = builder.create_element(
        permissions,
        "license",
        attributes={
            "license-type": template.license_type_attr,
            "xlink:href": template.ext_link_href,
        },
    )
    license_p = builder.create_element(license_element, "license-p")
    license_p.text = template.license_p
    builder.create_element(
        license_p,
        "ext-link",
        attributes={"xlink:href": template.ext_link_href, "ext-link-type": "uri"},
        text="Creative Commons Attribution License 4.0 (CC BY)",
    )


def _resolve_license_type(custom_meta: CustomMetaStore) -> str | None:
    """Resolve the source License Type to a `license_templates` key, or ``None`` to skip.

    Evidence-based (see module docstring): checked case-variant keys
    ("License Type"/"license type") both observed in real source data;
    a value is normalized to ``"CC-BY-4-0"`` when it looks like a CC-BY
    variant. When neither key exists at all, defaults to synthesizing
    CC-BY anyway — cs-2025-8827 has no such key yet still receives the
    identical license block in its real article.xml.
    """
    values = custom_meta.form_answers.get("license type") or custom_meta.form_answers.get(
        "License Type"
    )
    if values is None:
        return "CC-BY-4-0"
    for value in values:
        normalized = value.strip().upper().replace(" ", "-")
        if "CC-BY" in normalized:
            return "CC-BY-4-0"
    return None


# --- custom-meta-group pruning (BR-066–071/075) -------------------------------


def _build_custom_meta_group(
    builder: XmlDocumentBuilder,
    article_meta: Element,
    custom_meta: CustomMetaStore,
    rounds: RoundIndex,
    diagnostics: DiagnosticsCollector,
) -> None:
    has_form_answers = bool(custom_meta.form_answers.entries)
    has_files = bool(custom_meta.file_entries)
    if not has_form_answers and not has_files:
        diagnostics.info(_GENERATOR_NAME, "No custom-meta information available to prune")
        return

    group = builder.create_element(article_meta, "custom-meta-group")

    for entry in custom_meta.form_answers.entries:  # BR-071: deny-list, pass through unchanged
        for value in entry.values:
            add_custom_meta_entry(builder, group, entry.key, value)

    _add_latest_round_file_entries(builder, group, custom_meta, rounds, diagnostics)  # BR-066

    # BR-067 (QN_* reviewer-scorecard fields), BR-068 (decline reasons),
    # BR-069 (Decision Draft text) — all 3 categories are simply never
    # added here; nothing from `custom_meta.reviewer_scorecards`,
    # `.decline_reasons`, or `.decision_drafts` reaches article.xml.


def _add_latest_round_file_entries(
    builder: XmlDocumentBuilder,
    group: Element,
    custom_meta: CustomMetaStore,
    rounds: RoundIndex,
    diagnostics: DiagnosticsCollector,
) -> None:
    """BR-066: only the latest round's file-manifest entry survives per category.

    "Latest" is `~meca_engine.model.article.RoundInfo.is_latest` — the
    same, already-established round-ordering authority the rest of the
    ICAM uses (BR-010), never re-derived here.
    """
    if not custom_meta.file_entries:
        diagnostics.info(_GENERATOR_NAME, "No file-manifest custom-meta entries available")
        return
    latest_round_label = next(
        (round_info.label for round_info in rounds if round_info.is_latest), None
    )
    if latest_round_label is None:
        diagnostics.warn(
            _GENERATOR_NAME, "No latest round found; cannot filter file-manifest entries"
        )
        return
    latest_entries = [
        file_entry
        for file_entry in custom_meta.file_entries
        if file_entry.round_label == latest_round_label
    ]
    if not latest_entries:
        diagnostics.info(_GENERATOR_NAME, "No file-manifest entries found for the latest round")
    for file_entry in latest_entries:
        add_custom_meta_entry(
            builder,
            group,
            "file",
            f"{file_entry.category}: {file_entry.original_filename} ({file_entry.round_label})",
        )
