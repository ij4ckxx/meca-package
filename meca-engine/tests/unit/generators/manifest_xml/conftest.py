"""Shared fixtures for ManifestXmlGenerator unit tests."""

from __future__ import annotations

import pytest

from meca_engine.config.schema import (
    FeatureFlagsConfig,
    ItemTypeMappingConfig,
    JournalConfig,
    ManifestXmlConfig,
    MediaTypeConfig,
    PublisherConfig,
    RuntimeConfig,
)
from meca_engine.generators.context import GeneratorContext
from meca_engine.generators.diagnostics import DiagnosticsCollector
from meca_engine.generators.manifest_xml.generator import ManifestXmlGenerator
from meca_engine.generators.xml.namespaces import NamespaceManager
from meca_engine.logging_.structured_logger import get_logger
from meca_engine.model.article import (
    ArticleIdentity,
    ArticleMeta,
    ArticleModel,
    BodyFragment,
    CustomMetaStore,
    JournalMeta,
    ResolvedFile,
    RoundInfo,
)

_NAMESPACE_REGISTRY = {
    "xlink": "http://www.w3.org/1999/xlink",
    "meca-manifest": "https://manuscriptexchange.org/schema/manifest",
}


@pytest.fixture
def namespace_manager() -> NamespaceManager:
    return NamespaceManager(_NAMESPACE_REGISTRY)


@pytest.fixture
def manifest_xml_config() -> ManifestXmlConfig:
    return ManifestXmlConfig(
        doctype_public_id="-//MECA//DTD Manifest v1.0//en",
        doctype_system_id="./schema/manifest-1.0.dtd",
        encoding="UTF-8",
        manifest_version="1",
        pretty_indent_spaces=2,
        item_article_description_template=(
            "Article metadata exported from JATS (publisher-id: {publisher_id})"
        ),
        item_reviews_description=(
            "MECA reviews.xml generated from JATS custom-meta and history dates"
        ),
        item_transfer_description="MECA transfer.xml with source/destination info",
        article_filename_pattern="{article_id}_article.xml",
        reviews_filename_pattern="{article_id}_reviews.xml",
        transfer_filename_pattern="{article_id}_transfer.xml",
        file_item_id_prefix="file-",
        file_item_description_template="{category} — {original_filename} ({size_bytes} bytes)",
    )


@pytest.fixture
def item_type_mapping() -> ItemTypeMappingConfig:
    return ItemTypeMappingConfig(
        mappings={
            "manuscript": "manuscript",
            "figure": "figure",
            "licencetopublishform": "author agreement",
        },
        default_item_type="supplemental",
    )


@pytest.fixture
def media_type_config() -> MediaTypeConfig:
    return MediaTypeConfig(
        mappings={
            ".xml": "application/xml",
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".jpg": "image/jpeg",
        },
        unmapped_extension_policy="warn_and_default",
        unmapped_extension_default="application/octet-stream",
    )


@pytest.fixture
def manifest_xml_generator(
    namespace_manager: NamespaceManager,
    manifest_xml_config: ManifestXmlConfig,
    item_type_mapping: ItemTypeMappingConfig,
    media_type_config: MediaTypeConfig,
) -> ManifestXmlGenerator:
    return ManifestXmlGenerator(
        namespace_manager=namespace_manager,
        manifest_xml_config=manifest_xml_config,
        item_type_mapping=item_type_mapping,
        media_type_config=media_type_config,
    )


@pytest.fixture
def minimal_journal_config() -> JournalConfig:
    return JournalConfig(
        journal_id="clinical-science",
        display_name="Clinical Science",
        doi_prefix="10.1042",
        acronym="CS",
        article_type_mapping_ref="article-type-mapping.yaml",
        license_templates_ref="license-templates.yaml",
        doi_registry_scope="per-journal",
        publisher_id="portland-press",
    )


@pytest.fixture
def minimal_publisher_config() -> PublisherConfig:
    return PublisherConfig(
        publisher_id="portland-press",
        provider_name="Portland Press Limited",
        destination_provider_name="Silverchair",
        default_contact_policy="corresponding_author_email",
    )


@pytest.fixture
def minimal_feature_flags() -> FeatureFlagsConfig:
    return FeatureFlagsConfig(
        reviews_include_duplicate_correspondence=True,
        reviews_extended_history_scope=False,
        strict_replication_mode=False,
        allow_filename_fallback=True,
    )


def _minimal_article_meta() -> ArticleMeta:
    return ArticleMeta(
        display_channel_subject="Research Article",
        article_title="Untitled",
        contributors=(),
        affiliations=(),
    )


def build_rich_article_model(article_id: str = "cs-2025-0001") -> ArticleModel:
    """Build an `ArticleModel` exercising every manifest.xml-relevant ICAM field."""
    return ArticleModel(
        identity=ArticleIdentity(
            article_id=article_id,
            publisher_id_value="EX-2025-001",
            doi_article_id_value="ex-2025-001",
            journal_id="clinical-science",
            source_object_key=f"{article_id}/{article_id}.xml",
        ),
        journal_meta=JournalMeta(
            journal_title="Journal of Examples", issn_ppub=None, issn_epub=None, publisher_name=""
        ),
        article_meta=_minimal_article_meta(),
        body_fragment=BodyFragment(raw_xml_fragment=""),
        custom_meta=CustomMetaStore(),
        rounds=(
            RoundInfo(label="Original", sequence_number=1, is_latest=False),
            RoundInfo(label="R1", sequence_number=2, is_latest=True),
        ),
        resolved_files=(
            ResolvedFile(
                round_label="R1",
                category="manuscript",
                original_filename="manuscript",
                staged_physical_path="/staged/R1/manuscript.docx",
                checksum="a" * 64,
                size_bytes=1024,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ResolvedFile(
                round_label="R1",
                category="figure",
                original_filename="fig1",
                staged_physical_path="/staged/R1/fig1.jpg",
                checksum="b" * 64,
                size_bytes=2048,
                media_type="image/jpeg",
            ),
            ResolvedFile(
                round_label="Original",
                category="manuscript",
                original_filename="manuscript",
                staged_physical_path="/staged/Original/manuscript.docx",
                checksum="c" * 64,
                size_bytes=512,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        ),
    )


def build_empty_article_model(article_id: str = "cs-2025-0002") -> ArticleModel:
    """Build the smallest structurally-valid `ArticleModel` — no files, no rounds."""
    return ArticleModel(
        identity=ArticleIdentity(
            article_id=article_id,
            publisher_id_value="",
            doi_article_id_value="ex-2025-002",
            journal_id="",
            source_object_key=f"{article_id}/{article_id}.xml",
        ),
        journal_meta=JournalMeta(
            journal_title="", issn_ppub=None, issn_epub=None, publisher_name=""
        ),
        article_meta=_minimal_article_meta(),
        body_fragment=BodyFragment(raw_xml_fragment=""),
        custom_meta=CustomMetaStore(),
        rounds=(),
        resolved_files=(),
    )


@pytest.fixture
def rich_context(
    minimal_journal_config: JournalConfig,
    minimal_publisher_config: PublisherConfig,
    minimal_feature_flags: FeatureFlagsConfig,
) -> GeneratorContext:
    return GeneratorContext(
        model=build_rich_article_model(),
        runtime_config=_placeholder_runtime_config(),
        journal_config=minimal_journal_config,
        publisher_config=minimal_publisher_config,
        feature_flags=minimal_feature_flags,
        logger=get_logger("test.manifest_xml"),
        diagnostics=DiagnosticsCollector(),
    )


@pytest.fixture
def empty_context(
    minimal_journal_config: JournalConfig,
    minimal_publisher_config: PublisherConfig,
    minimal_feature_flags: FeatureFlagsConfig,
) -> GeneratorContext:
    return GeneratorContext(
        model=build_empty_article_model(),
        runtime_config=_placeholder_runtime_config(),
        journal_config=minimal_journal_config,
        publisher_config=minimal_publisher_config,
        feature_flags=minimal_feature_flags,
        logger=get_logger("test.manifest_xml"),
        diagnostics=DiagnosticsCollector(),
    )


def _placeholder_runtime_config() -> RuntimeConfig:
    from meca_engine.config.schema import (
        CheckpointSettings,
        ConcurrencySettings,
        DashboardSettings,
        DoiRegistrySettings,
        InputSettings,
        LoggingSettings,
        OutputSettings,
        PackagingSettings,
        RetrySettings,
        StagingSettings,
        ValidationSettings,
    )

    return RuntimeConfig(
        concurrency=ConcurrencySettings(worker_count=1, mechanism="process_pool"),
        retry=RetrySettings(
            max_attempts=1,
            backoff_base_seconds=1.0,
            backoff_multiplier=1.0,
            backoff_max_seconds=1.0,
        ),
        validation=ValidationSettings(
            dtd_validation_enabled=False, severity_block_threshold="HIGH"
        ),
        staging=StagingSettings(strategy="full_local_staging", working_dir_root="/tmp"),
        output=OutputSettings(operational_bucket="x", archival_bucket="x"),
        checkpoint=CheckpointSettings(backend="x"),
        doi_registry=DoiRegistrySettings(backend="x"),
        packaging=PackagingSettings(
            zip_compression="deflated",
            zip_compresslevel=6,
            staging_subdir_name="package_staging",
            overwrite_policy="fail",
        ),
        input=InputSettings(provider="LOCAL", local_path="./Input"),
        dashboard=DashboardSettings(reports_path="./archive_migration_validation"),
        logging=LoggingSettings(level="INFO"),
    )
