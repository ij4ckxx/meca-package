"""Golden-file regression: article.xml generation, against the 3 real reference packages.

Runs the complete Milestone 3 → 4 → 5B → 6B → 6C pipeline (parse →
extract → transform → raw.xml → article.xml) against each of the 3
real, manually-created reference packages and checks the generated
article.xml against specific, achievable facts about the corresponding
real `Output/*.zip` article.xml — **not** full-text/byte equality; see
`21_MILESTONE_6C_ARTICLE_XML_GENERATOR_REPORT.md`'s Golden Comparison
Report for the complete, classified difference list this test's
assertions are drawn from, including two confirmed, documented,
out-of-scope upstream defects (history `revision` date-type mismatch;
round-label/round-resolution data quality) that this test asserts
*around*, never silently past.

Marked `pytest.mark.golden` (see pyproject.toml's marker definition:
"mandatory merge gate") and deliberately outside `testpaths`; see
`tests/golden/README.md`.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element, fromstring

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
from meca_engine.generators.article_xml.generator import ArticleXmlGenerator
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

_REAL_ARTICLE_XML_BY_ARTICLE_ID = {
    "CS-2025-6808": ("MECA_cs-2025-6808.zip", "cs-2025-6808_article.xml"),
    "CS-2025-8493_C": ("MECA_CS-2025-8493_C.zip", "CS-2025-8493_C_article.xml"),
    "cs-2025-8827": ("MECA_cs-2025-8827.zip", "cs-2025-8827_article.xml"),
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
    logger = get_logger(f"golden.article_xml.{sample.article_id}")
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


def _real_article_xml_root(article_id: str) -> Element:
    zip_name, member_name = _REAL_ARTICLE_XML_BY_ARTICLE_ID[article_id]
    with zipfile.ZipFile(_OUTPUT_DIR / zip_name) as archive:
        return fromstring(archive.read(member_name))


def _placeholder_runtime_config() -> RuntimeConfig:
    # ArticleXmlGenerator reads none of these — a placeholder satisfying
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


def _build_context(model: ArticleModel, article_id: str) -> GeneratorContext:
    return GeneratorContext(
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
        logger=get_logger(f"golden.article_xml.{article_id}"),
        diagnostics=DiagnosticsCollector(),
    )


def _build_generator() -> ArticleXmlGenerator:
    loader = ConfigLoader(config_dir=_CONFIG_DIR, schema_dir=_SCHEMA_DIR)
    namespace_manager = NamespaceManager(loader.load_namespace_config().namespaces)
    raw_xml_generator = RawXmlGenerator(
        namespace_manager=namespace_manager, raw_xml_config=loader.load_raw_xml_config()
    )
    return ArticleXmlGenerator(
        raw_xml_generator=raw_xml_generator,
        namespace_manager=namespace_manager,
        article_xml_config=loader.load_article_xml_config(),
        article_type_mapping=loader.load_article_type_mapping(),
        license_templates=loader.load_license_templates(),
        publisher_abbreviation_mapping=loader.load_publisher_abbreviation_mapping(),
    )


def test_generated_article_xml_is_well_formed(real_sample: ExtractedSample) -> None:
    generator = _build_generator()
    model = _build_model(real_sample)
    context = _build_context(model, real_sample.article_id)

    result = generator.generate(context)
    generated_root = fromstring(result.document.xml_bytes)  # raises if not well-formed
    real_root = _real_article_xml_root(real_sample.article_id)

    # --- root / DTD (BR-052/057/074): identical across all 3 samples ---
    assert generated_root.get("article-type") == real_root.get("article-type") == "Original Study"
    assert generated_root.get("dtd-version") == real_root.get("dtd-version") == "1.2"

    # --- no <body>/<back> (source-data limitation, not a BR gap: none of
    # the 3 real reference packages carries either) ---
    assert generated_root.find("body") is None
    assert real_root.find("body") is None
    assert generated_root.find("back") is None
    assert real_root.find("back") is None

    # --- article identifiers (BR-058/059) ---
    real_ids = {
        el.get("pub-id-type"): el.text for el in real_root.findall("front/article-meta/article-id")
    }
    generated_ids = {
        el.get("pub-id-type"): el.text
        for el in generated_root.findall("front/article-meta/article-id")
    }
    assert generated_ids.get("publisher-id") == real_ids.get("publisher-id")
    assert generated_ids.get("doi") == real_ids.get("doi")

    # --- license synthesis (BR-063/064): identical boilerplate in all 3 ---
    real_license = real_root.find("front/article-meta/permissions/license")
    generated_license = generated_root.find("front/article-meta/permissions/license")
    assert real_license is not None, "every real sample carries a synthesized CC-BY license"
    assert generated_license is not None
    assert generated_license.get("license-type") == "open-access"  # BR-063: always applied
    assert (
        generated_license.get("{http://www.w3.org/1999/xlink}href")
        == "https://creativecommons.org/licenses/by/4.0/"
    )
    # CS-2025-6808's own reference package's outer `<license>` carries
    # neither `license-type` nor `xlink:href` (the other 2 samples carry
    # both) — a confirmed inconsistency between the 3 manually-created
    # reference packages themselves, not a code defect; this generator's
    # uniform, config-driven behavior matches 2/3 samples exactly and is
    # the one classified as correct. Only assert equality when the real
    # sample actually carries the attribute.
    if real_license.get("license-type") is not None:
        assert generated_license.get("license-type") == real_license.get("license-type")
    if real_license.get("{http://www.w3.org/1999/xlink}href") is not None:
        assert generated_license.get("{http://www.w3.org/1999/xlink}href") == real_license.get(
            "{http://www.w3.org/1999/xlink}href"
        )

    # The nested `<ext-link>`'s `xlink:href` is identical in all 3 real
    # samples regardless of the outer `<license>` attribute inconsistency.
    real_ext_link = real_root.find("front/article-meta/permissions/license/license-p/ext-link")
    generated_ext_link = generated_root.find(
        "front/article-meta/permissions/license/license-p/ext-link"
    )
    assert real_ext_link is not None
    assert generated_ext_link is not None
    assert generated_ext_link.get("{http://www.w3.org/1999/xlink}href") == real_ext_link.get(
        "{http://www.w3.org/1999/xlink}href"
    )

    # --- title (copied verbatim from raw.xml) ---
    assert generated_root.findtext(
        "front/article-meta/title-group/article-title"
    ) == real_root.findtext("front/article-meta/title-group/article-title")

    # --- fixed by the Milestone 6E transformation corrections ---
    # `history`'s middle date (`rev-recd`/`revision` in the 3 real
    # samples) previously never survived `TransformationCoordinator` —
    # `coordinator.py` looked for a literal `"revised"` date-type that no
    # real sample uses. Fixed to accept the evidence-confirmed synonym
    # set; all 3 history dates (by count and value) now reach article.xml.
    # The middle date's own `date-type` *string* is still normalized to
    # raw.xml's fixed "received"/"revised"/"accepted" vocabulary
    # (`generators/raw_xml/generator.py::_build_history`, unchanged,
    # out of this corrective milestone's scope) rather than preserving
    # the source's own literal "rev-recd"/"revision" text — a separate,
    # pre-existing, narrower BR-047 fidelity gap, not asserted here. See
    # `25_MILESTONE_6E_TRANSFORMATION_CORRECTIONS_REPORT.md`.
    real_dates = real_root.findall("front/article-meta/history/date")
    generated_dates = generated_root.findall("front/article-meta/history/date")
    assert len(generated_dates) == len(real_dates) == 3

    def _ymd(date_element: Element) -> tuple[str | None, str | None, str | None]:
        return (
            date_element.findtext("year"),
            date_element.findtext("month"),
            date_element.findtext("day"),
        )

    assert {_ymd(d) for d in generated_dates} == {_ymd(d) for d in real_dates}

    # --- confirmed, documented gaps: never asserted equal here ---
    # contrib-group/aff structural richness (multi-group source content,
    # `author-comment`, duplicate `xref`s) — inherited unchanged from
    # raw.xml's own already-documented BR-039 gap, not new to article.xml.
    # custom-meta-group's exact entry set — BR-066's file-manifest
    # filtering is evidence-correct but starved by `round_resolver.py`'s
    # own, separately-confirmed round-label defect; see the report.
