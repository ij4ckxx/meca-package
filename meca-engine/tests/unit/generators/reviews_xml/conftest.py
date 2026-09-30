"""Shared fixtures for ReviewsXmlGenerator unit tests."""

from __future__ import annotations

import pytest

from meca_engine.config.schema import (
    FeatureFlagsConfig,
    JournalConfig,
    PublisherConfig,
    ReviewsXmlConfig,
    RuntimeConfig,
)
from meca_engine.generators.context import GeneratorContext
from meca_engine.generators.diagnostics import DiagnosticsCollector
from meca_engine.generators.reviews_xml.generator import ReviewsXmlGenerator
from meca_engine.generators.xml.namespaces import NamespaceManager
from meca_engine.logging_.structured_logger import get_logger
from meca_engine.model.article import (
    ArticleIdentity,
    ArticleMeta,
    ArticleModel,
    BodyFragment,
    CustomMetaStore,
    JournalMeta,
    RoundInfo,
)

_NAMESPACE_REGISTRY = {
    "xlink": "http://www.w3.org/1999/xlink",
    "ali": "http://www.niso.org/schemas/ali/1.0/",
    "meca-reviews": "https://manuscriptexchange.org/schema/reviews",
}


@pytest.fixture
def namespace_manager() -> NamespaceManager:
    return NamespaceManager(_NAMESPACE_REGISTRY)


@pytest.fixture
def reviews_xml_config() -> ReviewsXmlConfig:
    return ReviewsXmlConfig(
        doctype_public_id="-//MECA//DTD Reviews v1.0//en",
        doctype_system_id="../DTD/reviews-1.0.dtd",
        encoding="UTF-8",
        content_version="1.0",
        pretty_indent_spaces=2,
        blinding="single",
        permission_to_publish="yes",
        permission_to_transfer="yes",
        review_item_data_type="text",
        reviews_filename_pattern="{article_id}_reviews.xml",
        scorecard_review_item_title="Reviewer Scorecard Responses",
        decline_review_item_title="Reviewer Assignment Status",
        decision_review_item_title="Editorial Decision",
        duplicate_correspondence_review_item_title="Correspondence Log Entry",
        extended_history_review_item_title="Workflow History Entry",
    )


@pytest.fixture
def reviews_xml_generator(
    namespace_manager: NamespaceManager, reviews_xml_config: ReviewsXmlConfig
) -> ReviewsXmlGenerator:
    return ReviewsXmlGenerator(
        namespace_manager=namespace_manager, reviews_xml_config=reviews_xml_config
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
def enabled_feature_flags() -> FeatureFlagsConfig:
    return FeatureFlagsConfig(
        reviews_include_duplicate_correspondence=True,
        reviews_extended_history_scope=True,
        strict_replication_mode=False,
        allow_filename_fallback=True,
    )


@pytest.fixture
def disabled_feature_flags() -> FeatureFlagsConfig:
    return FeatureFlagsConfig(
        reviews_include_duplicate_correspondence=False,
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


def build_article_model(
    *,
    article_id: str = "cs-2025-0001",
    custom_meta: CustomMetaStore | None = None,
    rounds: tuple[RoundInfo, ...] = (),
) -> ArticleModel:
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
        custom_meta=custom_meta if custom_meta is not None else CustomMetaStore(),
        rounds=rounds,
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
        logger=get_logger("test.reviews_xml"),
        diagnostics=DiagnosticsCollector(),
    )


@pytest.fixture
def rich_context(
    minimal_journal_config: JournalConfig,
    minimal_publisher_config: PublisherConfig,
    enabled_feature_flags: FeatureFlagsConfig,
) -> GeneratorContext:
    from meca_engine.model.article import DecisionDraft, DeclineReason, ReviewerScorecard
    from meca_engine.model.enums import ReviewOutcomeStatus

    custom_meta = CustomMetaStore(
        reviewer_scorecards=(
            ReviewerScorecard(
                round_label="Original",
                reviewer_name="Jane Reviewer",
                reviewer_email="jane@example.com",
                outcome_status=ReviewOutcomeStatus.COMPLETED,
                answers=(("QN_01", "Yes"), ("QN_02", "No")),
            ),
        ),
        decline_reasons=(
            DeclineReason(
                round_label="Original",
                reviewer_name="Declined Reviewer",
                reason_text="Unavailable at this time",
            ),
        ),
        decision_drafts=(
            DecisionDraft(round_label="Original", decision_text="Accepted with minor revisions."),
        ),
    )
    model = build_article_model(
        custom_meta=custom_meta,
        rounds=(RoundInfo(label="Original", sequence_number=1, is_latest=True),),
    )
    return build_context(
        model,
        journal_config=minimal_journal_config,
        publisher_config=minimal_publisher_config,
        feature_flags=enabled_feature_flags,
    )


@pytest.fixture
def empty_context(
    minimal_journal_config: JournalConfig,
    minimal_publisher_config: PublisherConfig,
    enabled_feature_flags: FeatureFlagsConfig,
) -> GeneratorContext:
    model = build_article_model()
    return build_context(
        model,
        journal_config=minimal_journal_config,
        publisher_config=minimal_publisher_config,
        feature_flags=enabled_feature_flags,
    )
