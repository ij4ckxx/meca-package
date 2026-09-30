"""Golden-file regression: manifest.xml generation, against the 3 real reference packages.

Runs the complete Milestone 3 → 4 → 5B → 6D pipeline (parse → extract →
transform → generate) against each of the 3 real, manually-created
reference packages and checks the generated manifest.xml against
specific, achievable facts about the corresponding real `Output/*.zip`
manifest.xml — **not** full-text/byte equality; see
`23_MILESTONE_6D_MANIFEST_XML_GENERATOR_REPORT.md`'s Golden Comparison
Report for the complete, classified difference list this test's
assertions are drawn from, including the confirmed upstream custom-meta
completeness gap (already documented against article.xml in Milestone
6C, reconfirmed here) that this test asserts *around*, never silently
past: every href this generator produces is verified a subset of the
real manifest's hrefs, never a superset or a mismatch.

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
from meca_engine.generators.manifest_xml.generator import ManifestXmlGenerator
from meca_engine.generators.xml.namespaces import NamespaceManager
from meca_engine.logging_ import get_logger
from meca_engine.transform.coordinator import TransformationCoordinator

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from meca_engine.model.article import ArticleModel

    from .conftest import ExtractedSample

pytestmark = [pytest.mark.golden]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "config-schema"
_OUTPUT_DIR = _REPO_ROOT / "Output"

_REAL_MANIFEST_XML_BY_ARTICLE_ID = {
    "CS-2025-6808": ("MECA_cs-2025-6808.zip", "cs-2025-6808_manifest.xml"),
    "CS-2025-8493_C": ("MECA_CS-2025-8493_C.zip", "CS-2025-8493_C_manifest.xml"),
    "cs-2025-8827": ("MECA_cs-2025-8827.zip", "cs-2025-8827_manifest.xml"),
}

_MANIFEST_NS = {
    "m": "https://manuscriptexchange.org/schema/manifest",
    "xlink": "http://www.w3.org/1999/xlink",
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
    logger = get_logger(f"golden.manifest_xml.{sample.article_id}")
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


def _real_manifest_xml_root(article_id: str) -> Element:
    zip_name, member_name = _REAL_MANIFEST_XML_BY_ARTICLE_ID[article_id]
    with zipfile.ZipFile(_OUTPUT_DIR / zip_name) as archive:
        return fromstring(archive.read(member_name))


def _hrefs(root: Element) -> set[str | None]:
    return {
        item.find("m:instance", _MANIFEST_NS).get(  # type: ignore[union-attr]
            "{http://www.w3.org/1999/xlink}href"
        )
        for item in root.findall("m:item", _MANIFEST_NS)[3:]
    }


def _placeholder_runtime_config() -> RuntimeConfig:
    # ManifestXmlGenerator reads none of these — a placeholder satisfying
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


def _build_generator() -> ManifestXmlGenerator:
    loader = ConfigLoader(config_dir=_CONFIG_DIR, schema_dir=_SCHEMA_DIR)
    namespace_manager = NamespaceManager(loader.load_namespace_config().namespaces)
    return ManifestXmlGenerator(
        namespace_manager=namespace_manager,
        manifest_xml_config=loader.load_manifest_xml_config(),
        item_type_mapping=loader.load_item_type_mapping(),
        media_type_config=loader.load_media_type_config(),
    )


def test_generated_manifest_xml_is_well_formed(real_sample: ExtractedSample) -> None:
    generator = _build_generator()
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
        logger=get_logger(f"golden.manifest_xml.{real_sample.article_id}"),
        diagnostics=DiagnosticsCollector(),
    )

    result = generator.generate(context)
    generated_root = fromstring(result.document.xml_bytes)  # raises if not well-formed
    real_root = _real_manifest_xml_root(real_sample.article_id)

    # --- root / DOCTYPE (BR-076/086/087/095): identical across all 3 ---
    assert (
        generated_root.tag
        == real_root.tag
        == "{https://manuscriptexchange.org/schema/manifest}manifest"
    )
    assert generated_root.get("manifest-version") == real_root.get("manifest-version") == "1"

    # --- 3 fixed items, in order (BR-077/079/080/092) ---
    generated_items = generated_root.findall("m:item", _MANIFEST_NS)
    real_items = real_root.findall("m:item", _MANIFEST_NS)
    assert [item.get("id") for item in generated_items[:3]] == [
        "item-article",
        "item-reviews",
        "item-transfer",
    ]
    assert [item.get("id") for item in real_items[:3]] == [
        "item-article",
        "item-reviews",
        "item-transfer",
    ]

    generated_article_description = generated_items[0].findtext(
        "m:item-description", namespaces=_MANIFEST_NS
    )
    real_article_description = real_items[0].findtext("m:item-description", namespaces=_MANIFEST_NS)
    assert (
        generated_article_description == real_article_description
    )  # BR-080: verbatim publisher-id

    real_fixed_hrefs = {
        item.find("m:instance", _MANIFEST_NS).get(  # type: ignore[union-attr]
            "{http://www.w3.org/1999/xlink}href"
        )
        for item in real_items[:3]
    }
    generated_fixed_hrefs = {
        item.find("m:instance", _MANIFEST_NS).get(  # type: ignore[union-attr]
            "{http://www.w3.org/1999/xlink}href"
        )
        for item in generated_items[:3]
    }
    # Case-insensitive: CS-2025-6808's real Output package lower-cases its
    # article_id in every generated filename even though its own Input
    # folder name is mixed-case ("CS-2025-6808") — the same kind of
    # sample-specific source/output casing inconsistency already
    # documented for `journal_id` in Milestone 6B's Golden Comparison
    # Report (ADR-028), now observed for `article_id` too, isolated to
    # this one sample (the other 2 samples' hrefs match exactly,
    # case included). See the Golden Comparison Report.
    assert {href.lower() for href in generated_fixed_hrefs if href} == {
        href.lower() for href in real_fixed_hrefs if href
    }

    # --- file items: every generated href is a confirmed, verified subset
    # of the real manifest's hrefs (see module docstring + Golden
    # Comparison Report for the confirmed upstream shortfall) ---
    generated_file_hrefs = _hrefs(generated_root)
    real_file_hrefs = _hrefs(real_root)
    assert generated_file_hrefs <= real_file_hrefs
    assert generated_file_hrefs, "at least one file item must be generated for every real sample"

    # --- CONFIRMED, currently-live BR-083 ordering mismatch (Generator
    # Suite Review, Milestone 6H) — asserted explicitly here as a
    # regression tripwire, not silently left unverified. Root cause:
    # `RoundInfo.label` (from `<article-version-type>`, always
    # `"Original"` on all 3 real samples per Milestone 6E §1.4/§8) never
    # equals the physical round-folder label `"R1"` — so this
    # generator's round-index lookup only ever resolves `"Original"`
    # (which sorts first, using its real sequence number), while every
    # `"R1"` file is diagnosed "not in the round index" and sorted last.
    # The real manifest.xml puts `"R1"` first (the actually-latest
    # round) on every multi-round sample. This is NOT a bug in this
    # generator's sort algorithm (already correct and unit-tested against
    # a synthetic 3-round fixture) — it is the direct, now fully
    # empirically-confirmed (3/3 samples) consequence of the
    # already-documented, deliberately-not-fixed `RoundInfo` semantic
    # mismatch. Fixing it would require either inventing an unevidenced
    # round-name mapping (explicitly forbidden: "do not introduce
    # additional round inference") or a business-confirmed change to
    # `round_resolver.py` (out of this generator's layer). See
    # `31_GENERATOR_SUITE_REVIEW_REPORT.md` and the Technical Debt
    # Register for the full analysis.
    def _round_order_of_first_appearance(items: list[Element]) -> list[str]:
        order: list[str] = []
        for item in items:
            instance = item.find("m:instance", _MANIFEST_NS)
            href = (
                instance.get("{http://www.w3.org/1999/xlink}href") if instance is not None else None
            )
            if not href:
                continue
            round_label = href.split("/")[1]
            if round_label not in order:
                order.append(round_label)
        return order

    real_file_items = real_items[3:]
    generated_file_items = generated_items[3:]
    real_round_order = _round_order_of_first_appearance(real_file_items)
    generated_round_order = _round_order_of_first_appearance(generated_file_items)
    if len(real_round_order) > 1:
        assert real_round_order[0] == "R1", (
            "expected real evidence's own confirmed round order (R1 first) — "
            "if this fails, real evidence changed and this whole finding needs "
            "re-verification"
        )
        assert generated_round_order[0] == "Original", (
            "expected this generator's own confirmed, currently-live BR-083 "
            "ordering mismatch (Original sorts first here, R1 sorts first in "
            "real evidence) — if this now passes, the RoundInfo semantic "
            "mismatch has been resolved and this whole finding should be "
            "revisited, re-classified, and this assertion updated/removed"
        )

    # --- item-type mapping (BR-078) agrees for every href in common ---
    real_item_type_by_href = {
        item.find("m:instance", _MANIFEST_NS).get(  # type: ignore[union-attr]
            "{http://www.w3.org/1999/xlink}href"
        ): item.get("item-type")
        for item in real_items[3:]
    }
    for item in generated_items[3:]:
        href = item.find("m:instance", _MANIFEST_NS).get(  # type: ignore[union-attr]
            "{http://www.w3.org/1999/xlink}href"
        )
        assert item.get("item-type") == real_item_type_by_href[href]

    # --- media-type resolution (BR-081): every generated value is a
    # plausible, non-empty MIME string; NOT asserted equal to the real
    # sample's own value — ADR-008 confirms all 3 real reference packages
    # use *legacy* Office MIME types (`.docx`→`application/msword`,
    # `.xlsx`→`application/vnd.ms-excel`) while `media-types.yaml` was
    # deliberately configured with *modern* OOXML types per ADR-008's own
    # recommended default (Option 2), pending business confirmation — a
    # documented, config-driven business-rule difference, not a code
    # defect. See the Golden Comparison Report. ---
    for item in generated_items[3:]:
        instance = item.find("m:instance", _MANIFEST_NS)
        assert instance is not None
        media_type = instance.get("media-type")
        assert media_type and "/" in media_type

    # --- confirmed, documented gaps: never asserted equal here ---
    # File item COUNT and item-description text — the real reference
    # packages' own item-description is a confirmed BR-084 defect
    # (naive concatenation), not replicated; file-item count shortfall
    # traces to the same custom-meta completeness gap already documented
    # against article.xml (Milestone 6C's Golden Comparison Report);
    # media-type text is ADR-008's legacy-vs-modern divergence, above.
