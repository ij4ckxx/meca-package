"""Shared fixtures for Generator Framework unit tests."""

from __future__ import annotations

import pytest

from meca_engine.config.schema import (
    CheckpointSettings,
    ConcurrencySettings,
    DashboardSettings,
    DoiRegistrySettings,
    FeatureFlagsConfig,
    InputSettings,
    JournalConfig,
    LoggingSettings,
    OutputSettings,
    PackagingSettings,
    PublisherConfig,
    RetrySettings,
    RuntimeConfig,
    StagingSettings,
    ValidationSettings,
)
from meca_engine.generators.context import GeneratorContext
from meca_engine.generators.diagnostics import DiagnosticsCollector
from meca_engine.logging_.structured_logger import get_logger
from meca_engine.model.article import (
    ArticleIdentity,
    ArticleMeta,
    ArticleModel,
    BodyFragment,
    CustomMetaStore,
    JournalMeta,
)


def build_minimal_article_model(article_id: str = "cs-2025-0001") -> ArticleModel:
    """Build the smallest structurally-complete `ArticleModel` for framework tests.

    Generator-framework tests only need *an* `ArticleModel` to thread
    through a `GeneratorContext` — no test in this package inspects its
    content, so every optional field is left at its default.
    """
    return ArticleModel(
        identity=ArticleIdentity(
            article_id=article_id,
            publisher_id_value="EX-2025-001",
            doi_article_id_value="EX-2025-001",
            journal_id="clinical-science",
            source_object_key=f"{article_id}/{article_id}.xml",
        ),
        journal_meta=JournalMeta(
            journal_title="Journal of Examples",
            issn_ppub="1234-5678",
            issn_epub="8765-4321",
            publisher_name="Example Press",
        ),
        article_meta=ArticleMeta(
            display_channel_subject="Research Article",
            article_title="A Study of Example Practices",
            contributors=(),
            affiliations=(),
        ),
        body_fragment=BodyFragment(raw_xml_fragment="<body/>"),
        custom_meta=CustomMetaStore(),
        rounds=(),
        resolved_files=(),
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
def minimal_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        concurrency=ConcurrencySettings(worker_count=4, mechanism="process_pool"),
        retry=RetrySettings(
            max_attempts=3,
            backoff_base_seconds=1.0,
            backoff_multiplier=2.0,
            backoff_max_seconds=30.0,
        ),
        validation=ValidationSettings(dtd_validation_enabled=True, severity_block_threshold="HIGH"),
        staging=StagingSettings(strategy="full_local_staging", working_dir_root="/tmp/staging"),
        output=OutputSettings(
            operational_bucket="test-operational", archival_bucket="test-archival"
        ),
        checkpoint=CheckpointSettings(backend="postgres"),
        doi_registry=DoiRegistrySettings(backend="postgres"),
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


@pytest.fixture
def minimal_feature_flags() -> FeatureFlagsConfig:
    return FeatureFlagsConfig(
        reviews_include_duplicate_correspondence=True,
        reviews_extended_history_scope=False,
        strict_replication_mode=False,
        allow_filename_fallback=True,
    )


@pytest.fixture
def generator_context(
    minimal_journal_config: JournalConfig,
    minimal_publisher_config: PublisherConfig,
    minimal_runtime_config: RuntimeConfig,
    minimal_feature_flags: FeatureFlagsConfig,
) -> GeneratorContext:
    return GeneratorContext(
        model=build_minimal_article_model(),
        runtime_config=minimal_runtime_config,
        journal_config=minimal_journal_config,
        publisher_config=minimal_publisher_config,
        feature_flags=minimal_feature_flags,
        logger=get_logger("test.generators"),
        diagnostics=DiagnosticsCollector(),
    )
