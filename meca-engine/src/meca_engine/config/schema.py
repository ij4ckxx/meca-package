"""Typed configuration dataclasses.

Defines the shape of every configuration file described in
12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §5. All dataclasses are frozen
(immutable once constructed), matching the ICAM's immutability philosophy
(11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §3.7) applied to configuration:
once loaded for a run, configuration must never be mutated by any consumer.

Note on scope (Milestone 1 — Foundation only): these dataclasses define the
*shape* of journal/publisher/license/media-type/article-type configuration
so that the loading and validation machinery can be fully built and tested
now. The actual business-value content of those files (e.g. a real journal's
acronym, real license text, real media-type mappings) is deliberately left
unpopulated in ``config/`` until the relevant ADRs are confirmed — see
09_FINAL_READINESS_REPORT.md and 02_ARCHITECTURE_DECISION_RECORDS.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from meca_engine.constants import Environment


@dataclass(frozen=True)
class JournalConfig:
    """Per-journal constants (12_LLD_03 §5.2).

    Attributes:
        journal_id: Matches the Kriyadocs ``journal-id[@journal-id-type=publisher-id]``
            value, lower-cased, used as the config lookup key (ADR-028).
        display_name: Human-readable journal title.
        doi_prefix: The journal's DOI registrant prefix (Business Rule Book BR-059).
        acronym: The journal acronym used in ``transfer.xml`` (ADR-007 — must
            be explicitly confirmed per journal before population; see
            ``schemas/config-schema/journal.schema.json`` for the placeholder
            sentinel value the loader rejects).
        article_type_mapping_ref: Reference to the article-type mapping table
            this journal uses (ADR-001).
        license_templates_ref: Reference to the license-template table this
            journal uses (ADR-002).
        doi_registry_scope: DOI uniqueness validation scope for this journal
            (ADR-015) — one of ``"per-journal"``, ``"per-run"``, ``"global"``.
        publisher_id: Foreign key into the publisher configuration.
    """

    journal_id: str
    display_name: str
    doi_prefix: str
    acronym: str
    article_type_mapping_ref: str
    license_templates_ref: str
    doi_registry_scope: str
    publisher_id: str


@dataclass(frozen=True)
class PublisherConfig:
    """Per-publisher constants (12_LLD_03 §5.3).

    Attributes:
        publisher_id: Config lookup key, referenced by ``JournalConfig.publisher_id``.
        provider_name: The source provider name for ``transfer.xml`` (Business
            Rule Book BR-128).
        destination_provider_name: The destination provider name for
            ``transfer.xml`` (Business Rule Book BR-134).
        default_contact_policy: How the primary contact email is selected
            when multiple corresponding authors exist (ADR-006's resolved
            answer) — one of ``"corresponding_author_email"`` or a future
            alternative policy name.
    """

    publisher_id: str
    provider_name: str
    destination_provider_name: str
    default_contact_policy: str


@dataclass(frozen=True)
class LicenseTemplate:
    """A single License Type's boilerplate text (12_LLD_03 §5.4).

    Attributes:
        license_type_attr: The ``<license license-type="...">`` attribute value.
        license_p: The generated ``<license-p>`` boilerplate text.
        ext_link_href: The license URL embedded in the generated ``<ext-link>``.
    """

    license_type_attr: str
    license_p: str
    ext_link_href: str


@dataclass(frozen=True)
class LicenseTemplatesConfig:
    """Every configured License Type's boilerplate, keyed by source value (12_LLD_03 §5.4).

    Populated in Milestone 6C with the one evidence-confirmed entry
    (Business Rule Book BR-063/064: identical license-p text and
    `ext-link` URL, 3/3 samples) — see `config/license-templates.yaml`.
    An unmapped License Type has no entry here by design (ADR-002/BR-065:
    no sample demonstrates non-CC-BY handling) — `ArticleXmlGenerator`
    raises `LicenseMappingError` rather than guess.

    Attributes:
        templates: Source License Type value to its `LicenseTemplate`.
    """

    templates: Mapping[str, LicenseTemplate]


@dataclass(frozen=True)
class MediaTypeConfig:
    """Extension-to-MIME-type lookup configuration (12_LLD_03 §5.6).

    Attributes:
        mappings: Extension (including leading dot, lower-case) to MIME type.
        unmapped_extension_policy: One of ``"warn_and_default"`` or ``"fail"``
            (ADR-009).
        unmapped_extension_default: The MIME type used when
            ``unmapped_extension_policy`` is ``"warn_and_default"``.
    """

    mappings: Mapping[str, str]
    unmapped_extension_policy: str
    unmapped_extension_default: str


@dataclass(frozen=True)
class ArticleTypeMappingConfig:
    """``display-channel`` → ``article.xml`` ``article-type`` lookup (ADR-001 / BR-057).

    Added in Milestone 5C to close a gap the Architecture Review found:
    this schema was named in 10_LLD_01 §1 and referenced by
    ``ArticleMeta.display_channel_subject`` but never actually created.

    Attributes:
        mappings: Source ``display-channel`` text to ``article-type``.
        default_article_type: The value used for any unmapped
            ``display-channel`` — all 3 real reference packages resolve
            to the same value here (BR-057: "Original Study" observed
            for every ``display-channel`` seen), but ADR-001 flags this
            as still requiring business confirmation for an unseen type.
    """

    mappings: Mapping[str, str]
    default_article_type: str


@dataclass(frozen=True)
class PublisherAbbreviationMappingConfig:
    """``journal-id[@journal-id-type="publisher-id"]`` → publisher abbreviation lookup (BR-164).

    Deterministic and closed by design: unlike
    :class:`ArticleTypeMappingConfig`, there is no default/fallback
    value — an unrecognized publisher-id must never be guessed at, only
    ever left unchanged and surfaced as a Validation Only finding.

    Attributes:
        mappings: ``identity.journal_id`` (ADR-028's lower-cased config
            lookup key, e.g. ``"cs"``, ``"bcj"``) to the publisher's own
            journal abbreviation (e.g. ``"CS"``, ``"BCJ"``).
    """

    mappings: Mapping[str, str]


@dataclass(frozen=True)
class ItemTypeMappingConfig:
    """Custom-meta file ``category`` → ``manifest.xml`` item-type lookup (BR-078).

    Added in Milestone 5C to close a gap the Architecture Review found:
    this schema was named in 10_LLD_01 §1 and referenced by
    ``ResolvedFile.category`` but never actually created.

    Attributes:
        mappings: Source ``category`` to manifest item-type.
        default_item_type: The value used for any unmapped category
            (BR-019: the category vocabulary is open, not a fixed enum
            — BR-078 confirms ``"supplemental"`` as the default).
    """

    mappings: Mapping[str, str]
    default_item_type: str


@dataclass(frozen=True)
class ConcurrencySettings:
    """Worker concurrency configuration (12_LLD_03 §5.7; ADR-021)."""

    worker_count: int
    mechanism: str


@dataclass(frozen=True)
class RetrySettings:
    """Retry/backoff configuration (12_LLD_03 §5.7; ADR-023)."""

    max_attempts: int
    backoff_base_seconds: float
    backoff_multiplier: float
    backoff_max_seconds: float


@dataclass(frozen=True)
class ValidationSettings:
    """Validation Engine runtime configuration (12_LLD_03 §5.7; ADR-024, ADR-025)."""

    dtd_validation_enabled: bool
    severity_block_threshold: str


@dataclass(frozen=True)
class StagingSettings:
    """Working-folder staging configuration (12_LLD_03 §5.7; ADR-020)."""

    strategy: str
    working_dir_root: str


@dataclass(frozen=True)
class OutputSettings:
    """Output/archival location configuration (12_LLD_03 §5.7; ADR-029).

    Attributes:
        operational_bucket: The S3 operational-storage bucket (existing,
            Milestone 1 field — unused until the S3 output path is built).
        archival_bucket: The S3 archival-storage bucket (same status).
        provider: Archive Migration Platform Phase 1 (ADR-030) — which
            :class:`~meca_engine.providers.output.OutputProvider`
            implementation to use: ``"LOCAL"``, ``"S3"``, or ``"SFTP"``.
        local_path: Where :class:`~meca_engine.providers.output.LocalOutputProvider`
            writes generated packages. Deliberately never defaults to
            ``"./Output"`` — that folder holds hand-curated reference
            packages that must never be overwritten; see the Phase 1
            Configuration Guide.
    """

    operational_bucket: str
    archival_bucket: str
    provider: str = "LOCAL"
    local_path: str = "./archive_migration_validation/generated_packages"


@dataclass(frozen=True)
class CheckpointSettings:
    """Checkpoint Store backend selection (12_LLD_03 §5.7)."""

    backend: str


@dataclass(frozen=True)
class DoiRegistrySettings:
    """DOI Registry backend selection (12_LLD_03 §5.7)."""

    backend: str


@dataclass(frozen=True)
class InputSettings:
    """Input source configuration (Archive Migration Platform Phase 1, ADR-030).

    Attributes:
        provider: Which :class:`~meca_engine.providers.input.InputProvider`
            implementation to use: ``"LOCAL"`` or ``"S3"``.
        local_path: Where :class:`~meca_engine.providers.input.LocalInputProvider`
            reads article zip files from.
    """

    provider: str
    local_path: str


@dataclass(frozen=True)
class DashboardSettings:
    """Dashboard/reporting output location (Archive Migration Platform Phase 1)."""

    reports_path: str


@dataclass(frozen=True)
class LoggingSettings:
    """Logging configuration (Archive Migration Platform Phase 1)."""

    level: str


@dataclass(frozen=True)
class PackagingSettings:
    """Package Assembly configuration (Milestone 7).

    Attributes:
        zip_compression: ``zipfile`` compression method name — ``"deflated"``
            or ``"stored"`` (no config surface previously existed for this;
            added this milestone following the same operational-settings
            pattern as :class:`ConcurrencySettings`/:class:`RetrySettings`).
        zip_compresslevel: Compression level passed to ``zipfile.ZipFile``
            when ``zip_compression`` is ``"deflated"``; ``None`` uses the
            zipfile module's own default.
        staging_subdir_name: Name of the per-article working subdirectory
            created under ``StagingSettings.working_dir_root`` while a
            package is being assembled (13_LLD_04 §9.4's "own working
            subdirectory... deleted after successful publish or terminal
            failure" policy).
        overwrite_policy: Asset Copy Engine behavior when a destination
            file already exists — ``"fail"``, ``"overwrite"``, or ``"skip"``.
    """

    zip_compression: str
    zip_compresslevel: int | None
    staging_subdir_name: str
    overwrite_policy: str


@dataclass(frozen=True)
class RuntimeConfig:
    """Aggregate operational runtime settings (12_LLD_03 §5.7).

    Unlike journal/publisher/license/media-type configuration, this is
    operational, not business-value, data — populated in Milestone 1.
    ``input``/``dashboard``/``logging`` were added in Archive Migration
    Platform Phase 1 (ADR-030) — extending this existing aggregate rather
    than introducing a second configuration mechanism.
    """

    concurrency: ConcurrencySettings
    retry: RetrySettings
    validation: ValidationSettings
    staging: StagingSettings
    output: OutputSettings
    checkpoint: CheckpointSettings
    doi_registry: DoiRegistrySettings
    packaging: PackagingSettings
    input: InputSettings
    dashboard: DashboardSettings
    logging: LoggingSettings


@dataclass(frozen=True)
class FeatureFlagsConfig:
    """Behavioral toggles (12_LLD_03 §5.8).

    Operational/behavioral, not business-value, data — populated in
    Milestone 1 with the defaults recommended by their governing ADRs.

    Attributes:
        allow_filename_fallback: Milestone 10 (ADR-032) — when ``True``
            (the default), a `FileEntry` with no declared name but a
            usable `declared_path_hint` has its filename derived from
            that path for generation purposes, recorded as a
            ``BR013_FALLBACK_FILENAME_FROM_PATH`` warning, instead of
            raising `FileReferenceMissingError`. ``False`` restores the
            pre-Milestone-10 strict behavior. The first feature flag
            read by `extraction`/`transform` code, not just `generators`.
    """

    reviews_include_duplicate_correspondence: bool
    reviews_extended_history_scope: bool
    strict_replication_mode: bool
    allow_filename_fallback: bool


@dataclass(frozen=True)
class S3EnvironmentSettings:
    """AWS S3 environment-variable-sourced settings.

    Attributes:
        bucket_name: Target S3 bucket name.
        prefix: Key prefix within the bucket (e.g. 'ppl/').
        region: AWS region (e.g. 'us-east-1').
    """

    bucket_name: str = ""
    prefix: str = ""
    region: str = "us-east-1"


@dataclass(frozen=True)
class SftpEnvironmentSettings:
    """SFTP destination environment-variable-sourced settings.

    Attributes:
        host: SFTP server hostname.
        port: SFTP server port (default 22).
        user: SFTP username.
        password: SFTP password.
        remote_dir: Remote folder path to store packages (default '/sftp/meca').
        key_path: Path to optional SSH private key file.
        delete_local_after_upload: Whether to remove local ZIP after successful SFTP upload.
    """

    host: str = ""
    port: int = 22
    user: str = ""
    password: str = ""
    remote_dir: str = "/sftp/meca"
    key_path: str = ""
    delete_local_after_upload: bool = False


@dataclass(frozen=True)
class EnvironmentSettings:
    """Environment-variable-sourced settings (12_LLD_03 §5; 14_LLD_05 §12.3).

    Attributes:
        environment: Which deployment environment this process is running in.
        config_dir: Root directory containing the ``config/`` YAML tree.
        debug_logging_enabled: Whether the debug logging category is enabled.
        s3: S3 bucket and prefix configuration.
        sftp: SFTP destination connection configuration.
    """

    environment: Environment
    config_dir: Path
    debug_logging_enabled: bool
    s3: S3EnvironmentSettings = field(default_factory=S3EnvironmentSettings)
    sftp: SftpEnvironmentSettings = field(default_factory=SftpEnvironmentSettings)


@dataclass(frozen=True)
class NamespaceConfig:
    """XML namespace prefix-to-URI registry (Generator Framework, Milestone 6A).

    Confirmed against the 3 real reference packages' generated output
    (``Output/*.zip``): JATS documents (``raw.xml``/``article.xml``) carry
    no namespace of their own (validated by DTD, not namespace) and only
    ever declare ``xlink``/``mml``/``xsi``/``ali`` as auxiliary prefixes;
    MECA's own ``manifest.xml``/``reviews.xml``/``transfer.xml`` each
    declare one unprefixed default namespace. This config is a flat
    prefix→URI registry — which prefixes a given document actually
    declares is a generator (not framework) decision.

    Attributes:
        namespaces: Prefix (empty string reserved for "no prefix / a
            document's own default namespace key") to namespace URI.
    """

    namespaces: Mapping[str, str]


@dataclass(frozen=True)
class RawXmlConfig:
    """raw.xml generator settings (Milestone 6B; Business Rule Book BR-036–050).

    Every value here is a documented, evidence-confirmed constant from
    the Business Rule Book — externalized to configuration (rather than
    a literal in `generators.raw_xml.generator`) per this milestone's
    "no hard-coded article types" instruction, and per ADR-001's own
    precedent of keeping even "currently always the same value" facts
    externally configurable.

    Attributes:
        doctype_public_id: BR-036's DOCTYPE public identifier.
        doctype_system_id: BR-036's DOCTYPE system identifier.
        article_type: BR-040's constant ``article-type`` attribute value.
        dtd_version: BR-049's constant ``dtd-version`` attribute value.
        default_xml_lang: BR-050's ``xml:lang`` value — a default, since
            no ICAM field carries a per-article source language today
            (a documented gap; see the Milestone 6B Architecture
            Compliance Report).
        encoding: BR-038's declared output encoding.
        namespace_prefixes: Which `config/namespaces.yaml`-registered
            prefixes BR-037 requires unconditionally on the root element,
            in declaration order.
        pretty_indent_spaces: BR-044's "pretty-printed" confirmed against
            all 3 real reference packages to mean one element per line
            with **zero** indentation width regardless of nesting depth
            (not the hierarchically-indented style
            :class:`~meca_engine.generators.xml.builder.XmlDocumentBuilder`
            defaults to) — externalized here rather than hard-coded so
            the evidence, not an assumption, drives the value.
    """

    doctype_public_id: str
    doctype_system_id: str
    article_type: str
    dtd_version: str
    default_xml_lang: str
    encoding: str
    namespace_prefixes: tuple[str, ...]
    pretty_indent_spaces: int


@dataclass(frozen=True)
class ArticleXmlConfig:
    """article.xml generator settings (Milestone 6C; Business Rule Book BR-051–075).

    Every value here is a documented, evidence-confirmed constant —
    externalized per this milestone's "no hard-coded business values"
    instruction.

    Attributes:
        doctype_public_id: BR-052's DOCTYPE public identifier (JATS
            Archiving & Interchange DTD v1.2).
        doctype_system_id: BR-052's DOCTYPE system identifier.
        dtd_version: BR-074's constant ``dtd-version`` attribute value.
        encoding: BR-053's declared output encoding (lower-case, unlike
            raw.xml's upper-case BR-038).
        pretty_indent_spaces: Same BR-044-confirmed zero-indent style
            raw.xml uses — no independent evidence contradicts it for
            article.xml (both are produced by the same pipeline stage).
    """

    doctype_public_id: str
    doctype_system_id: str
    dtd_version: str
    encoding: str
    pretty_indent_spaces: int


@dataclass(frozen=True)
class ManifestXmlConfig:
    """manifest.xml generator settings (Milestone 6D; Business Rule Book BR-076–095).

    Every value here is a documented, evidence-confirmed constant —
    externalized per this milestone's "no hard-coded publisher-specific
    values" instruction. ``file_item_id_prefix`` and
    ``file_item_description_template`` deliberately do **not** replicate
    the 3 real reference packages' own observed patterns — BR-084/BR-085
    each confirm the observed pattern is a clerical defect in those
    packages, not a rule, and each documents its own recommended
    replacement; these fields implement that replacement.

    Attributes:
        doctype_public_id: BR-076's DOCTYPE public identifier.
        doctype_system_id: BR-095's DOCTYPE system identifier (a
            documentary relative reference, never resolved/fetched).
        encoding: BR-086's declared output encoding (upper-case, like
            raw.xml's BR-038, unlike article.xml's lower-case BR-053).
        manifest_version: BR-087's constant ``manifest-version`` attribute.
        pretty_indent_spaces: Confirmed 2-space hierarchical indentation
            from direct inspection of all 3 real reference packages —
            unlike raw.xml/article.xml's zero-indent style (BR-044),
            manifest.xml's real output uses ordinary nested indentation.
        item_article_description_template: BR-079/080's ``item-article``
            description template, interpolated with the verbatim
            ``article-id[@pub-id-type=publisher-id]`` value.
        item_reviews_description: BR-079's fully-constant ``item-reviews``
            description.
        item_transfer_description: BR-079's fully-constant
            ``item-transfer`` description.
        article_filename_pattern: The sibling article.xml filename
            pattern (BR-073, restated here so this generator never
            depends on the `ArticleXmlGenerator` instance itself — see
            the Manifest Decision Log).
        reviews_filename_pattern: The sibling reviews.xml filename
            pattern (not yet a generator this milestone; the fixed
            manifest item still references it by name, per BR-077).
        transfer_filename_pattern: The sibling transfer.xml filename
            pattern (same rationale as ``reviews_filename_pattern``).
        file_item_id_prefix: BR-085's recommended deterministic id
            scheme's prefix — ``f"{file_item_id_prefix}{sequence}"``.
        file_item_description_template: BR-084's recommended clean
            replacement for the observed naive-concatenation defect.
    """

    doctype_public_id: str
    doctype_system_id: str
    encoding: str
    manifest_version: str
    pretty_indent_spaces: int
    item_article_description_template: str
    item_reviews_description: str
    item_transfer_description: str
    article_filename_pattern: str
    reviews_filename_pattern: str
    transfer_filename_pattern: str
    file_item_id_prefix: str
    file_item_description_template: str


@dataclass(frozen=True)
class ReviewsXmlConfig:
    """reviews.xml generator settings (Milestone 6F; Business Rule Book BR-096–125).

    Every value here is a documented, evidence-confirmed constant —
    externalized per this milestone's "no hard-coded workflow values"
    instruction. BR-098's canonical per-review attribute schema is only
    2/3-confirmed (CS-2025-6808's own reference package omits all four
    attributes — a superseded/incomplete pattern, not replicated); the
    values here implement the canonical (2/3) target shape.

    Attributes:
        doctype_public_id: BR-096's DOCTYPE public identifier.
        doctype_system_id: BR-096's DOCTYPE system identifier (a
            documentary relative reference, never resolved/fetched).
        encoding: BR-120's declared output encoding (upper-case).
        content_version: BR-097's constant root attribute.
        pretty_indent_spaces: Confirmed 2-space hierarchical indentation
            from direct inspection of all 3 real reference packages.
        blinding: BR-100's confirmed constant ``<review>`` attribute.
        permission_to_publish: BR-101's confirmed constant.
        permission_to_transfer: BR-101's confirmed constant.
        review_item_data_type: The canonical (2/3) ``review-item-data``
            type attribute value observed alongside BR-098's schema.
        reviews_filename_pattern: BR-122's filename pattern.
        scorecard_review_item_title: Title for the one review-item this
            generator can honestly build from a completed
            ``ReviewerScorecard`` (its ``QN_*`` answers) — see the
            Reviews Decision Log for why BR-103/104's richer
            recommendation/comments split is not attempted (no such
            field exists in the ICAM on any of the 3 real samples).
        decline_review_item_title: Title for a declined/terminated
            reviewer's status-only review-item (BR-106).
        decision_review_item_title: Title for an editorial decision's
            review-item (BR-109/110).
        duplicate_correspondence_review_item_title: Title for a
            duplicate correspondence-log review-item, gated by
            ``FeatureFlagsConfig.reviews_include_duplicate_correspondence``
            (ADR-004, BR-116) — never exercised by any of the 3 real
            samples today (``WorkflowLog.events`` is always empty), but
            structurally ready and synthetic-fixture-tested (ADR-013's
            established precedent for un-evidenced-but-approved paths).
        extended_history_review_item_title: Title for an extended-scope
            (screening query / editor reassignment / author-suggested
            reviewer / production query) review-item, gated by
            ``FeatureFlagsConfig.reviews_extended_history_scope``
            (ADR-005, BR-111/117/118/119) — same "structurally ready,
            never exercised by real data" status as above.
    """

    doctype_public_id: str
    doctype_system_id: str
    encoding: str
    content_version: str
    pretty_indent_spaces: int
    blinding: str
    permission_to_publish: str
    permission_to_transfer: str
    review_item_data_type: str
    reviews_filename_pattern: str
    scorecard_review_item_title: str
    decline_review_item_title: str
    decision_review_item_title: str
    duplicate_correspondence_review_item_title: str
    extended_history_review_item_title: str


@dataclass(frozen=True)
class TransferXmlConfig:
    """transfer.xml generator settings (Milestone 6G; Business Rule Book BR-126–140).

    Every value here is a documented, evidence-confirmed constant —
    externalized per this milestone's "no hard-coded publisher/journal/
    destination values" instruction. Notably absent: the journal
    acronym (BR-133/135) — ADR-007 is unresolved (2/3 real samples use
    `"CLINSCI"`, present nowhere in any source XML; 1/3 uses `"CS"`) and
    its own recommended fallback is an external per-journal config
    table, already provided by `JournalConfig.acronym` — this generator
    reads that field directly rather than duplicating a second acronym
    source here.

    Attributes:
        doctype_public_id: BR-126's DOCTYPE public identifier.
        doctype_system_id: BR-126's DOCTYPE system identifier (a
            documentary relative reference, never resolved/fetched).
        transfer_version: The constant root ``transfer-version`` attribute.
        publication_type: The constant ``publication/@type`` attribute
            (observed as ``"journal"`` in all 3 real samples).
        pretty_indent_spaces: Confirmed 2-space hierarchical indentation
            from direct inspection of all 3 real reference packages.
        authentication_code_separator: BR-136's pipe separator between
            the two repeated ``publisher-id`` halves.
        processing_instructions: BR-137's exactly-2 fixed processing
            steps, in sequence order (1-based sequence number is this
            tuple's own index + 1, never a separately-configured number
            that could drift out of sync with the list order).
        processing_comments_template: BR-138's template, interpolated
            with the sibling raw.xml filename.
        raw_xml_filename_pattern: The sibling raw.xml filename pattern
            (BR-048, restated here so this generator never depends on
            the `RawXmlGenerator` instance itself — see the Transfer
            Decision Log, following manifest.xml's own established
            precedent for sibling-filename references).
        transfer_filename_pattern: BR-139's filename pattern.
        source_section_comment: The `<!-- ... -->` heading text preceding
            `<transfer-source>` in all 3 real samples (cosmetic, but
            free to replicate exactly via the framework's own
            `XmlDocumentBuilder.add_comment`).
        destination_section_comment: Same, preceding `<destination>`.
        instructions_section_comment: Same, preceding
            `<processing-instructions>`.
    """

    doctype_public_id: str
    doctype_system_id: str
    transfer_version: str
    publication_type: str
    pretty_indent_spaces: int
    authentication_code_separator: str
    processing_instructions: tuple[str, ...]
    processing_comments_template: str
    raw_xml_filename_pattern: str
    transfer_filename_pattern: str
    source_section_comment: str
    destination_section_comment: str
    instructions_section_comment: str


@dataclass(frozen=True)
class AppConfig:
    """The fully-loaded, aggregate application configuration for one run.

    Attributes:
        environment_settings: Environment-variable-sourced settings.
        runtime: Operational runtime settings.
        feature_flags: Behavioral toggles.
        journals: All loaded journal configurations, keyed by ``journal_id``.
        publishers: All loaded publisher configurations, keyed by ``publisher_id``.
    """

    environment_settings: EnvironmentSettings
    runtime: RuntimeConfig
    feature_flags: FeatureFlagsConfig
    journals: Mapping[str, JournalConfig]
    publishers: Mapping[str, PublisherConfig]
