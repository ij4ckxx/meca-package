"""Golden-file regression: raw.xml generation, against the 3 real reference packages.

Runs the complete Milestone 3 → 4 → 5B → 6B pipeline (parse → extract →
transform → generate) against each of the 3 real, manually-created
reference packages and checks the generated raw.xml against specific,
achievable facts about the corresponding real `Output/*.zip` raw.xml —
**not** full-text/byte equality, which several documented, evidence-based
ICAM gaps make unreachable today (see
`20_MILESTONE_6B_RAW_XML_GENERATOR_REPORT.md`'s Golden Comparison Report
for the complete, classified difference list this test's assertions are
drawn from).

Marked `pytest.mark.golden` (see pyproject.toml's marker definition:
"mandatory merge gate") and deliberately outside `testpaths`; see
`tests/golden/README.md`.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree.ElementTree import fromstring

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
    MediaTypeConfig,
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
from meca_engine.generators.context import GeneratorContext
from meca_engine.generators.diagnostics import DiagnosticsCollector
from meca_engine.generators.raw_xml.generator import RawXmlGenerator
from meca_engine.generators.xml.namespaces import NamespaceManager
from meca_engine.logging_ import get_logger
from meca_engine.transform.coordinator import TransformationCoordinator

if TYPE_CHECKING:
    from meca_engine.model.article import ArticleModel

    from .conftest import ExtractedSample

pytestmark = [pytest.mark.golden]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "config-schema"
_OUTPUT_DIR = _REPO_ROOT / "Output"

_REAL_RAW_XML_BY_ARTICLE_ID = {
    "CS-2025-6808": ("MECA_cs-2025-6808.zip", "cs-2025-6808_raw.xml"),
    "CS-2025-8493_C": ("MECA_CS-2025-8493_C.zip", "CS-2025-8493_C_raw.xml"),
    "cs-2025-8827": ("MECA_cs-2025-8827.zip", "cs-2025-8827_raw.xml"),
}

_MEDIA_TYPE_CONFIG = MediaTypeConfig(
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


def _build_model(sample: ExtractedSample) -> ArticleModel:
    logger = get_logger(f"golden.raw_xml.{sample.article_id}")
    loader = XmlLoader(logger)
    document = loader.load(sample.xml_path)
    bundle = extract_all_metadata(document, logger)
    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG, logger=logger)
    return coordinator.build_model(
        article_id=sample.article_id,
        source_object_key=f"{sample.article_id}/{sample.xml_path.name}",
        staged_root=str(sample.staged_root),
        parsed_document=document,
        extraction_bundle=bundle,
    )


def _real_raw_xml_bytes(article_id: str) -> bytes:
    zip_name, member_name = _REAL_RAW_XML_BY_ARTICLE_ID[article_id]
    with zipfile.ZipFile(_OUTPUT_DIR / zip_name) as archive:
        return archive.read(member_name)


def _placeholder_runtime_config() -> RuntimeConfig:
    # RawXmlGenerator reads none of these — a placeholder satisfying
    # GeneratorContext's required fields, not a business-value fixture.
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


def test_generated_raw_xml_is_well_formed(real_sample: ExtractedSample) -> None:
    loader = ConfigLoader(config_dir=_CONFIG_DIR, schema_dir=_SCHEMA_DIR)
    namespace_manager = NamespaceManager(loader.load_namespace_config().namespaces)
    raw_xml_config = loader.load_raw_xml_config()
    generator = RawXmlGenerator(namespace_manager=namespace_manager, raw_xml_config=raw_xml_config)

    model = _build_model(real_sample)
    context = GeneratorContext(
        model=model,
        runtime_config=_placeholder_runtime_config(),
        journal_config=JournalConfig(
            journal_id=model.identity.journal_id,
            display_name="Clinical Science",
            doi_prefix="10.1042",
            acronym="CS",
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
            reviews_extended_history_scope=False,
            strict_replication_mode=False,
            allow_filename_fallback=True,
        ),
        logger=get_logger(f"golden.raw_xml.{real_sample.article_id}"),
        diagnostics=DiagnosticsCollector(),
    )

    result = generator.generate(context)
    generated_root = fromstring(result.document.xml_bytes)  # raises if not well-formed
    real_root = fromstring(_real_raw_xml_bytes(real_sample.article_id))

    # --- structural facts confirmed achievable from the current ICAM ---
    assert generated_root.get("article-type") == real_root.get("article-type") == "research-article"
    assert generated_root.get("dtd-version") == real_root.get("dtd-version") == "1.3"

    real_article_ids = {
        el.get("pub-id-type"): el.text for el in real_root.findall("front/article-meta/article-id")
    }
    generated_article_ids = {
        el.get("pub-id-type"): el.text
        for el in generated_root.findall("front/article-meta/article-id")
    }
    assert generated_article_ids.get("publisher-id") == real_article_ids.get("publisher-id")
    assert generated_article_ids.get("doi") == real_article_ids.get("doi")

    real_title = real_root.findtext("front/article-meta/title-group/article-title")
    generated_title = generated_root.findtext("front/article-meta/title-group/article-title")
    assert generated_title == real_title

    # --- body: verbatim copy (BR-043) ---
    # Not exact-set equality: the real reference package's body has
    # already had Kriyadocs tracked-change/copyediting wrapper elements
    # (<span data-class="jrnlLQCRef">, <named-content content-type="ins
    # .../del ...">) removed — the Input/*.zip source this test builds
    # from still carries them all, so the generated body's id set is a
    # large superset of the real one (confirmed: 294/296 real ids found
    # in the generated set for CS-2025-6808). Classified a **source-data
    # difference** (the Input snapshot appears to predate the Output
    # snapshot's final copyediting acceptance), not a BR-041 gap — see
    # the Golden Comparison Report for the full evidence and reasoning.
    real_body_ids = {el.get("id") for el in real_root.findall("body//*[@id]")}
    generated_body_ids = {el.get("id") for el in generated_root.findall("body//*[@id]")}
    assert real_body_ids, "real sample body must carry at least one id (BR-039)"
    overlap_ratio = len(real_body_ids & generated_body_ids) / len(real_body_ids)
    assert overlap_ratio >= 0.9, f"body id overlap too low: {overlap_ratio:.1%}"

    # --- confirmed, documented gaps: never asserted equal here ---
    # journal-id casing (ADR-028 lower-casing), <back> (no ICAM source),
    # custom-meta-group verbatim structure/ids, contrib-group multi-group
    # structure — see the Golden Comparison Report for the full list.
