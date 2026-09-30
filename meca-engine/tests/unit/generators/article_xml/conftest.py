"""Shared fixtures for ArticleXmlGenerator unit tests."""

from __future__ import annotations

from datetime import date

import pytest

from meca_engine.config.schema import (
    ArticleTypeMappingConfig,
    ArticleXmlConfig,
    FeatureFlagsConfig,
    JournalConfig,
    LicenseTemplate,
    LicenseTemplatesConfig,
    PublisherAbbreviationMappingConfig,
    PublisherConfig,
    RawXmlConfig,
    RuntimeConfig,
)
from meca_engine.generators.article_xml.generator import ArticleXmlGenerator
from meca_engine.generators.context import GeneratorContext
from meca_engine.generators.diagnostics import DiagnosticsCollector
from meca_engine.generators.raw_xml.generator import RawXmlGenerator
from meca_engine.generators.xml.namespaces import NamespaceManager
from meca_engine.logging_.structured_logger import get_logger
from meca_engine.model.article import (
    Abstract,
    Affiliation,
    ArticleCounts,
    ArticleIdentity,
    ArticleMeta,
    ArticleModel,
    BodyFragment,
    Contributor,
    CorrespEmail,
    CustomMetaStore,
    FileEntry,
    FormAnswerBag,
    FormAnswerEntry,
    HistoryDates,
    JournalMeta,
    RoundInfo,
)
from meca_engine.model.enums import ContribType

_NAMESPACE_REGISTRY = {
    "mml": "http://www.w3.org/1998/Math/MathML",
    "xlink": "http://www.w3.org/1999/xlink",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "ali": "http://www.niso.org/schemas/ali/1.0/",
}


@pytest.fixture
def namespace_manager() -> NamespaceManager:
    return NamespaceManager(_NAMESPACE_REGISTRY)


@pytest.fixture
def raw_xml_config() -> RawXmlConfig:
    return RawXmlConfig(
        doctype_public_id="-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.3 20210610//EN",
        doctype_system_id="JATS-journalpublishing1-3.dtd",
        article_type="research-article",
        dtd_version="1.3",
        default_xml_lang="en",
        encoding="UTF-8",
        namespace_prefixes=("mml", "xlink", "xsi", "ali"),
        pretty_indent_spaces=0,
    )


@pytest.fixture
def article_xml_config() -> ArticleXmlConfig:
    return ArticleXmlConfig(
        doctype_public_id=(
            "-//NLM//DTD JATS (Z39.96) Journal Archiving and Interchange DTD v1.2 20190208//EN"
        ),
        doctype_system_id="https://jats.nlm.nih.gov/archiving/1.2/JATS-archivearticle1.dtd",
        dtd_version="1.2",
        encoding="utf-8",
        pretty_indent_spaces=0,
    )


@pytest.fixture
def article_type_mapping() -> ArticleTypeMappingConfig:
    return ArticleTypeMappingConfig(
        mappings={"Research Article": "Original Study"},
        default_article_type="Original Study",
    )


@pytest.fixture
def publisher_abbreviation_mapping() -> PublisherAbbreviationMappingConfig:
    return PublisherAbbreviationMappingConfig(mappings={"cs": "CS", "bcj": "BCJ"})


@pytest.fixture
def license_templates() -> LicenseTemplatesConfig:
    return LicenseTemplatesConfig(
        templates={
            "CC-BY-4-0": LicenseTemplate(
                license_type_attr="open-access",
                license_p=(
                    "This is an open access article published by Portland Press Limited on "
                    "behalf of the Biochemical Society and distributed under the Creative "
                    "Commons Attribution License 4.0 (CC BY)."
                ),
                ext_link_href="https://creativecommons.org/licenses/by/4.0/",
            )
        }
    )


@pytest.fixture
def raw_xml_generator(
    namespace_manager: NamespaceManager, raw_xml_config: RawXmlConfig
) -> RawXmlGenerator:
    return RawXmlGenerator(namespace_manager=namespace_manager, raw_xml_config=raw_xml_config)


@pytest.fixture
def article_xml_generator(
    raw_xml_generator: RawXmlGenerator,
    namespace_manager: NamespaceManager,
    article_xml_config: ArticleXmlConfig,
    article_type_mapping: ArticleTypeMappingConfig,
    license_templates: LicenseTemplatesConfig,
    publisher_abbreviation_mapping: PublisherAbbreviationMappingConfig,
) -> ArticleXmlGenerator:
    return ArticleXmlGenerator(
        raw_xml_generator=raw_xml_generator,
        namespace_manager=namespace_manager,
        article_xml_config=article_xml_config,
        article_type_mapping=article_type_mapping,
        license_templates=license_templates,
        publisher_abbreviation_mapping=publisher_abbreviation_mapping,
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


def build_rich_article_model(article_id: str = "cs-2025-0001") -> ArticleModel:
    """Build an `ArticleModel` exercising every article.xml-relevant ICAM field at least once."""
    author = Contributor(
        surname="Doe",
        given_names="Jane",
        contrib_type=ContribType.AUTHOR,
        email="jane.doe@example.com",
        orcid="0000-0001-2345-6789",
        affiliation_keys=(1,),
        is_corresponding=True,
        equal_contrib=True,
    )
    return ArticleModel(
        identity=ArticleIdentity(
            article_id=article_id,
            publisher_id_value="EX-2025-001",
            doi_article_id_value="ex-2025-001",
            journal_id="clinical-science",
            source_object_key=f"{article_id}/{article_id}.xml",
        ),
        journal_meta=JournalMeta(
            journal_title="Journal of Examples",
            issn_ppub="1234-5678",
            issn_epub="8765-4321",
            publisher_name="Example Press",
            abbrev_titles=(("pubmed", "J. Ex."),),
        ),
        article_meta=ArticleMeta(
            display_channel_subject="Research Article",
            article_title="A Study of Example Practices",
            contributors=(author,),
            affiliations=(
                Affiliation(model_key=1, institution="University of Example", country="USA"),
            ),
            corresponding_emails=(CorrespEmail(email="jane.doe@example.com"),),
            heading_subjects=("Cell Biology",),
            copyright_statement="© 2025 The Author(s).",
            copyright_year="2025",
            funding=("Example Foundation Grant 12345",),
            keywords=("examples", "testing"),
            counts=ArticleCounts(word_count=5000, ref_count=42, fig_count=3),
            history_dates=HistoryDates(
                received=date(2025, 1, 10), revision=date(2025, 2, 1), accepted=date(2025, 2, 20)
            ),
            abstracts=(Abstract(text="This study examines example practices."),),
        ),
        body_fragment=BodyFragment(
            raw_xml_fragment='<body id="b1"><title>Title Page</title></body>'
        ),
        custom_meta=CustomMetaStore(
            form_answers=FormAnswerBag(
                entries=(FormAnswerEntry(key="Authorship", values=("Yes",)),)
            ),
            file_entries=(
                FileEntry(
                    round_label="Original",
                    category="manuscript",
                    original_filename="manuscript_v1.docx",
                    declared_path_hint="Original/manuscript_v1.docx",
                    declared_size_bytes=1024,
                ),
                FileEntry(
                    round_label="R1",
                    category="manuscript",
                    original_filename="manuscript_v2.docx",
                    declared_path_hint="R1/manuscript_v2.docx",
                    declared_size_bytes=2048,
                ),
                FileEntry(
                    round_label="R1",
                    category="supplement",
                    original_filename="supplement.pdf",
                    declared_path_hint="R1/supplement.pdf",
                    declared_size_bytes=512,
                ),
            ),
        ),
        rounds=(
            RoundInfo(label="Original", sequence_number=1, is_latest=False),
            RoundInfo(label="R1", sequence_number=2, is_latest=True),
        ),
        resolved_files=(),
    )


def build_empty_article_model(article_id: str = "cs-2025-0002") -> ArticleModel:
    """Build the smallest structurally-valid `ArticleModel` — every *optional* field empty.

    ``doi_article_id_value`` is deliberately non-empty: BR-058's DOI is
    required input, not optional, so this fixture supplies it — a
    dedicated test (`test_missing_doi_article_id_raises_missing_doi_error`)
    covers the empty case explicitly instead.
    """
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
        article_meta=ArticleMeta(
            display_channel_subject="", article_title="Untitled", contributors=(), affiliations=()
        ),
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
        logger=get_logger("test.article_xml"),
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
        logger=get_logger("test.article_xml"),
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
