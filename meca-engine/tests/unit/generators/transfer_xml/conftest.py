"""Shared fixtures for TransferXmlGenerator unit tests."""

from __future__ import annotations

import pytest

from meca_engine.config.schema import (
    FeatureFlagsConfig,
    JournalConfig,
    PublisherConfig,
    RuntimeConfig,
    TransferXmlConfig,
)
from meca_engine.generators.context import GeneratorContext
from meca_engine.generators.diagnostics import DiagnosticsCollector
from meca_engine.generators.transfer_xml.generator import TransferXmlGenerator
from meca_engine.generators.xml.namespaces import NamespaceManager
from meca_engine.logging_.structured_logger import get_logger
from meca_engine.model.article import (
    ArticleIdentity,
    ArticleMeta,
    ArticleModel,
    BodyFragment,
    CorrespEmail,
    CustomMetaStore,
    JournalMeta,
)

_NAMESPACE_REGISTRY = {"meca-transfer": "https://manuscriptexchange.org/schema/transfer"}


@pytest.fixture
def namespace_manager() -> NamespaceManager:
    return NamespaceManager(_NAMESPACE_REGISTRY)


@pytest.fixture
def transfer_xml_config() -> TransferXmlConfig:
    return TransferXmlConfig(
        doctype_public_id="-//MECA//DTD Transfer v1.0//en",
        doctype_system_id="./schema/transfer-1.0.dtd",
        transfer_version="1.0",
        publication_type="journal",
        pretty_indent_spaces=2,
        authentication_code_separator="|",
        processing_instructions=("Validate Metadata", "Ingest Article Package"),
        processing_comments_template="Generated automatically from source JATS: {raw_xml_filename}",
        raw_xml_filename_pattern="{article_id}_raw.xml",
        transfer_filename_pattern="{article_id}_transfer.xml",
        source_section_comment="======== SOURCE ========",
        destination_section_comment="======== DESTINATION ========",
        instructions_section_comment="======== INSTRUCTIONS & PROVENANCE ========",
    )


@pytest.fixture
def transfer_xml_generator(
    namespace_manager: NamespaceManager, transfer_xml_config: TransferXmlConfig
) -> TransferXmlGenerator:
    return TransferXmlGenerator(
        namespace_manager=namespace_manager, transfer_xml_config=transfer_xml_config
    )


@pytest.fixture
def minimal_journal_config() -> JournalConfig:
    return JournalConfig(
        journal_id="clinical-science",
        display_name="Clinical Science",
        doi_prefix="10.1042",
        acronym="CLINSCI",
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
        reviews_extended_history_scope=True,
        strict_replication_mode=False,
        allow_filename_fallback=True,
    )


def build_article_model(
    *,
    article_id: str = "cs-2025-0001",
    publisher_id_value: str = "CS20250001",
    journal_title: str = "Journal of Examples",
    corresponding_emails: tuple[CorrespEmail, ...] = (CorrespEmail(email="jane@example.com"),),
) -> ArticleModel:
    return ArticleModel(
        identity=ArticleIdentity(
            article_id=article_id,
            publisher_id_value=publisher_id_value,
            doi_article_id_value="ex-2025-001",
            journal_id="clinical-science",
            source_object_key=f"{article_id}/{article_id}.xml",
        ),
        journal_meta=JournalMeta(
            journal_title=journal_title, issn_ppub=None, issn_epub=None, publisher_name=""
        ),
        article_meta=ArticleMeta(
            display_channel_subject="Research Article",
            article_title="Untitled",
            contributors=(),
            affiliations=(),
            corresponding_emails=corresponding_emails,
        ),
        body_fragment=BodyFragment(raw_xml_fragment=""),
        custom_meta=CustomMetaStore(),
        rounds=(),
        resolved_files=(),
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


def build_context(
    model: ArticleModel,
    *,
    journal_config: JournalConfig,
    publisher_config: PublisherConfig,
    feature_flags: FeatureFlagsConfig,
) -> GeneratorContext:
    return GeneratorContext(
        model=model,
        runtime_config=_placeholder_runtime_config(),
        journal_config=journal_config,
        publisher_config=publisher_config,
        feature_flags=feature_flags,
        logger=get_logger("test.transfer_xml"),
        diagnostics=DiagnosticsCollector(),
    )


@pytest.fixture
def rich_context(
    minimal_journal_config: JournalConfig,
    minimal_publisher_config: PublisherConfig,
    minimal_feature_flags: FeatureFlagsConfig,
) -> GeneratorContext:
    return build_context(
        build_article_model(),
        journal_config=minimal_journal_config,
        publisher_config=minimal_publisher_config,
        feature_flags=minimal_feature_flags,
    )


@pytest.fixture
def empty_context(
    minimal_journal_config: JournalConfig,
    minimal_publisher_config: PublisherConfig,
    minimal_feature_flags: FeatureFlagsConfig,
) -> GeneratorContext:
    model = build_article_model(publisher_id_value="", journal_title="", corresponding_emails=())
    return build_context(
        model,
        journal_config=replace_acronym(minimal_journal_config, ""),
        publisher_config=minimal_publisher_config,
        feature_flags=minimal_feature_flags,
    )


def replace_acronym(journal_config: JournalConfig, acronym: str) -> JournalConfig:
    from dataclasses import replace

    return replace(journal_config, acronym=acronym)
