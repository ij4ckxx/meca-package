"""Golden-file regression: complete Package Assembly, against the 3 real reference packages.

Runs the full Milestone 3 -> 4 -> 5B -> 6 -> 7 pipeline (parse -> extract
-> transform -> generate all 5 XMLs -> assemble) against each real sample
and verifies the resulting zip is structurally complete and internally
consistent with manifest.xml's own, already-verified (Milestone 6H) file
list — this is the one test that exercises every generator and
`PackageBuilder` together, the way a real production run would.

Marked `pytest.mark.golden` (see pyproject.toml's marker definition:
"mandatory merge gate") and deliberately outside `testpaths`; see
`tests/golden/README.md`.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from meca_engine.config.loader import ConfigLoader
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
from meca_engine.extraction.metadata_extraction import extract_all_metadata
from meca_engine.extraction.xml_loader import XmlLoader
from meca_engine.generators.article_xml.generator import ArticleXmlGenerator
from meca_engine.generators.context import GeneratorContext
from meca_engine.generators.diagnostics import DiagnosticsCollector
from meca_engine.generators.manifest_xml.generator import ManifestXmlGenerator
from meca_engine.generators.raw_xml.generator import RawXmlGenerator
from meca_engine.generators.reviews_xml.generator import ReviewsXmlGenerator
from meca_engine.generators.transfer_xml.generator import TransferXmlGenerator
from meca_engine.generators.xml.namespaces import NamespaceManager
from meca_engine.logging_ import get_logger
from meca_engine.packaging.asset_copy import AssetCopyService
from meca_engine.packaging.builder import PackageBuilder
from meca_engine.packaging.zip_builder import ZipBuilder
from meca_engine.registry.backends.in_memory import InMemoryDoiRegistry
from meca_engine.transform.coordinator import TransformationCoordinator

if TYPE_CHECKING:
    from meca_engine.model.article import ArticleModel

    from .conftest import ExtractedSample

pytestmark = [pytest.mark.golden]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "config-schema"

_REAL_ACRONYM_BY_ARTICLE_ID = {
    "CS-2025-6808": "CLINSCI",
    "CS-2025-8493_C": "CLINSCI",
    "cs-2025-8827": "CS",
}


def _build_model(sample: ExtractedSample) -> ArticleModel:
    from meca_engine.config.schema import MediaTypeConfig

    media_type_config = MediaTypeConfig(
        mappings={
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".pdf": "application/pdf",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
        unmapped_extension_policy="warn_and_default",
        unmapped_extension_default="application/octet-stream",
    )
    logger = get_logger(f"golden.package_assembly.{sample.article_id}")
    loader = XmlLoader(logger)
    document = loader.load(sample.xml_path)
    bundle = extract_all_metadata(document, logger)
    coordinator = TransformationCoordinator(media_type_config=media_type_config, logger=logger)
    return coordinator.build_model(
        article_id=sample.article_id,
        source_object_key=f"{sample.article_id}/{sample.xml_path.name}",
        staged_root=str(sample.staged_root),
        parsed_document=document,
        extraction_bundle=bundle,
    )


def _placeholder_runtime_config() -> RuntimeConfig:
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


def _build_package_builder(
    loader: ConfigLoader,
    namespace_manager: NamespaceManager,
    *,
    doi_registry: InMemoryDoiRegistry | None = None,
) -> PackageBuilder:
    media_type_config = loader.load_media_type_config()
    raw_generator = RawXmlGenerator(
        namespace_manager=namespace_manager, raw_xml_config=loader.load_raw_xml_config()
    )
    logger = get_logger("golden.package_assembly")
    return PackageBuilder(
        raw_generator=raw_generator,
        article_generator=ArticleXmlGenerator(
            namespace_manager=namespace_manager,
            article_xml_config=loader.load_article_xml_config(),
            article_type_mapping=loader.load_article_type_mapping(),
            license_templates=loader.load_license_templates(),
            publisher_abbreviation_mapping=loader.load_publisher_abbreviation_mapping(),
            raw_xml_generator=RawXmlGenerator(
                namespace_manager=namespace_manager, raw_xml_config=loader.load_raw_xml_config()
            ),
        ),
        manifest_generator=ManifestXmlGenerator(
            namespace_manager=namespace_manager,
            manifest_xml_config=loader.load_manifest_xml_config(),
            item_type_mapping=loader.load_item_type_mapping(),
            media_type_config=media_type_config,
        ),
        reviews_generator=ReviewsXmlGenerator(
            namespace_manager=namespace_manager, reviews_xml_config=loader.load_reviews_xml_config()
        ),
        transfer_generator=TransferXmlGenerator(
            namespace_manager=namespace_manager,
            transfer_xml_config=loader.load_transfer_xml_config(),
        ),
        namespace_manager=namespace_manager,
        asset_copy_service=AssetCopyService(overwrite_policy="fail", logger=logger),
        zip_builder=ZipBuilder(compression="deflated", compresslevel=6, logger=logger),
        logger=logger,
        doi_registry=doi_registry if doi_registry is not None else InMemoryDoiRegistry(),
    )


def test_package_assembly_produces_a_complete_self_consistent_zip(
    real_sample: ExtractedSample, tmp_path: Path
) -> None:
    loader = ConfigLoader(config_dir=_CONFIG_DIR, schema_dir=_SCHEMA_DIR)
    namespace_manager = NamespaceManager(loader.load_namespace_config().namespaces)
    context = _build_context(loader, real_sample)

    builder = _build_package_builder(loader, namespace_manager)
    output_root = tmp_path / "output"
    output_root.mkdir()

    staged_package = builder.build(context, output_root=output_root)

    # --- the zip exists and is a complete, well-formed archive ---
    assert staged_package.zip_path.is_file()
    with zipfile.ZipFile(staged_package.zip_path) as archive:
        assert archive.testzip() is None  # no corrupt member
        zip_names = set(archive.namelist())

    # --- every generated XML file is present, under its own filename ---
    assert set(staged_package.xml_filenames) <= zip_names
    assert len(staged_package.xml_filenames) == 5

    # --- every manifest-declared physical file is present at its href ---
    packaged_hrefs = {packaged_file.href for packaged_file in staged_package.packaged_files}
    assert packaged_hrefs <= zip_names
    assert len(packaged_hrefs) == len(staged_package.packaged_files)  # no href collisions

    # --- the DOI extracted from article.xml was successfully reserved ---
    assert staged_package.doi is not None
    assert staged_package.doi.startswith("10.1042/")

    # --- no staging artifacts survive a successful build ---
    assert not any(output_root.glob(".package-staging-*"))
    assert not any(output_root.glob(".MECA_*.zip.tmp"))


def _build_context(loader: ConfigLoader, real_sample: ExtractedSample) -> GeneratorContext:
    model = _build_model(real_sample)
    return GeneratorContext(
        model=model,
        runtime_config=_placeholder_runtime_config(),
        journal_config=JournalConfig(
            journal_id=model.identity.journal_id,
            display_name="Clinical Science",
            doi_prefix="10.1042",
            acronym=_REAL_ACRONYM_BY_ARTICLE_ID[real_sample.article_id],
            article_type_mapping_ref="article-type-mapping.yaml",
            license_templates_ref="license-templates.yaml",
            doi_registry_scope="per-journal",
            publisher_id="portland-press",
        ),
        publisher_config=PublisherConfig(
            publisher_id="portland-press",
            provider_name="Portland Press Limited",
            destination_provider_name="Silverchair",
            default_contact_policy="corresponding_author_email",
        ),
        feature_flags=FeatureFlagsConfig(
            reviews_include_duplicate_correspondence=True,
            reviews_extended_history_scope=True,
            strict_replication_mode=False,
            allow_filename_fallback=True,
        ),
        logger=get_logger(f"golden.package_assembly.{real_sample.article_id}"),
        diagnostics=DiagnosticsCollector(),
    )


def test_package_assembly_rejects_a_doi_already_reserved_by_another_article(
    real_sample: ExtractedSample, tmp_path: Path
) -> None:
    from meca_engine.exceptions.article_errors import DoiCollisionError

    loader = ConfigLoader(config_dir=_CONFIG_DIR, schema_dir=_SCHEMA_DIR)
    namespace_manager = NamespaceManager(loader.load_namespace_config().namespaces)

    # First build succeeds and reveals the real, generated DOI — never
    # reconstructed manually here, avoiding any duplication of BR-058's
    # DOI-generation logic inside this test.
    first_output_root = tmp_path / "first"
    first_output_root.mkdir()
    first_builder = _build_package_builder(loader, namespace_manager)
    first_result = first_builder.build(
        _build_context(loader, real_sample), output_root=first_output_root
    )
    assert first_result.doi is not None

    # A second, independent registry pre-loaded with that same DOI under a
    # different article_id simulates a genuine cross-article collision.
    colliding_registry = InMemoryDoiRegistry()
    colliding_registry.reserve(first_result.doi, article_id="SOME-OTHER-ARTICLE")
    second_builder = _build_package_builder(
        loader, namespace_manager, doi_registry=colliding_registry
    )
    second_output_root = tmp_path / "second"
    second_output_root.mkdir()

    with pytest.raises(DoiCollisionError):
        second_builder.build(_build_context(loader, real_sample), output_root=second_output_root)

    assert not any(second_output_root.glob("MECA_*.zip"))
    assert not any(second_output_root.glob(".package-staging-*"))
