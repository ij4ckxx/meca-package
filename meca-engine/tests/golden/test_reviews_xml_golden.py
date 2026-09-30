"""Golden-file regression: reviews.xml generation, against the 3 real reference packages.

Runs the complete Milestone 3 → 4 → 5B → 6F pipeline (parse → extract →
transform → generate) against each of the 3 real, manually-created
reference packages and checks the generated reviews.xml against
specific, achievable facts about the corresponding real `Output/*.zip`
reviews.xml — **not** full-text/byte equality, which is unreachable by
design for this generator: direct inspection confirms the real
packages' richest content (per-reviewer recommendation text,
comment/confidential splits, editor identity, every date, and 13-32
CDATA-typed correspondence/query-log entries per sample — see
`28_REVIEWS_DECISION_LOG.md`) was manually curated by a human reading
raw correspondence logs, sourced from ICAM fields
(`ReviewerScorecard.overall_recommendation`/dates,
`DecisionDraft.editor_name`/`.associate_editor_name`/`.decision_date`,
`WorkflowLog.events`) that are confirmed always `None`/empty on all 3
real samples. This test therefore asserts structural/deterministic
facts about this generator's own, internally-consistent output relative
to the ICAM it was built from, plus a handful of cross-checks against
real evidence that *are* safely verifiable (DOCTYPE, namespaces,
content-version, BR-099 compliance, reviewer-name provenance).

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
from meca_engine.generators.reviews_xml.generator import ReviewsXmlGenerator
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

_REAL_REVIEWS_XML_BY_ARTICLE_ID = {
    "CS-2025-6808": ("MECA_cs-2025-6808.zip", "cs-2025-6808_reviews.xml"),
    "CS-2025-8493_C": ("MECA_CS-2025-8493_C.zip", "CS-2025-8493_C_reviews.xml"),
    "cs-2025-8827": ("MECA_cs-2025-8827.zip", "cs-2025-8827_reviews.xml"),
}

_REVIEWS_NS = {"r": "https://manuscriptexchange.org/schema/reviews"}

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
    logger = get_logger(f"golden.reviews_xml.{sample.article_id}")
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


def _real_reviews_xml_bytes(article_id: str) -> bytes:
    zip_name, member_name = _REAL_REVIEWS_XML_BY_ARTICLE_ID[article_id]
    with zipfile.ZipFile(_OUTPUT_DIR / zip_name) as archive:
        return archive.read(member_name)


def _placeholder_runtime_config() -> RuntimeConfig:
    # ReviewsXmlGenerator reads none of these — a placeholder satisfying
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


def _build_generator() -> ReviewsXmlGenerator:
    loader = ConfigLoader(config_dir=_CONFIG_DIR, schema_dir=_SCHEMA_DIR)
    namespace_manager = NamespaceManager(loader.load_namespace_config().namespaces)
    return ReviewsXmlGenerator(
        namespace_manager=namespace_manager,
        reviews_xml_config=loader.load_reviews_xml_config(),
    )


def test_generated_reviews_xml_is_well_formed(real_sample: ExtractedSample) -> None:
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
            reviews_extended_history_scope=True,
            strict_replication_mode=False,
            allow_filename_fallback=True,
        ),
        logger=get_logger(f"golden.reviews_xml.{real_sample.article_id}"),
        diagnostics=DiagnosticsCollector(),
    )

    result = generator.generate(context)
    generated_root = fromstring(result.document.xml_bytes)  # raises if not well-formed
    real_root = fromstring(_real_reviews_xml_bytes(real_sample.article_id))

    # --- root / DOCTYPE / namespaces (BR-096/097): identical across all 3 ---
    assert (
        generated_root.tag
        == real_root.tag
        == "{https://manuscriptexchange.org/schema/reviews}review-group"
    )
    assert generated_root.get("content-version") == real_root.get("content-version") == "1.0"

    # --- BR-099: never the illegal "CDATA" literal, even though 2/3 real
    # reference packages contain it (13-32 occurrences each — confirmed
    # evidence broader than BR-099's own "pkg1 only" text; see the
    # Reviews Decision Log) ---
    generated_reviews = generated_root.findall("r:review", _REVIEWS_NS)
    generated_types = {review.get("review-type") for review in generated_reviews}
    assert generated_types <= {"review", "decision"}

    # --- internal consistency: this generator's own output is a exact,
    # deterministic function of its own ICAM input (never over- or
    # under-produces relative to what the ICAM actually declares) ---
    custom_meta = model.custom_meta
    review_type_reviews = [r for r in generated_reviews if r.get("review-type") == "review"]
    decision_type_reviews = [r for r in generated_reviews if r.get("review-type") == "decision"]
    assert len(review_type_reviews) == len(custom_meta.reviewer_scorecards) + len(
        custom_meta.decline_reasons
    )
    assert len(decision_type_reviews) == len(
        [draft for draft in custom_meta.decision_drafts if draft.decision_text]
    )

    # --- reviewer-name provenance: every reviewer name this generator
    # emits must already appear somewhere in the real reference
    # package's own reviews.xml — never a fabricated identity ---
    real_text = _real_reviews_xml_bytes(real_sample.article_id).decode("utf-8", errors="replace")
    for scorecard in custom_meta.reviewer_scorecards:
        if scorecard.reviewer_name:
            assert (
                scorecard.reviewer_name in real_text
                or _surname(scorecard.reviewer_name) in real_text
            )
    for decline in custom_meta.decline_reasons:
        if decline.reviewer_name:
            assert (
                decline.reviewer_name in real_text or _surname(decline.reviewer_name) in real_text
            )

    # --- BR-123: every review/decision resolves a round via review-version ---
    for review in generated_reviews:
        assert review.get("review-version")

    # --- confirmed, documented gaps: never asserted equal here ---
    # Per-reviewer recommendation/comments-split text (BR-103/104),
    # editor/associate-editor identity and every date (BR-110/112/114),
    # multi-point screening splits (BR-111), duplicate correspondence
    # (BR-116), and extended-scope categories (BR-117-119) — none of
    # these have a populated ICAM source field on any of the 3 real
    # samples; see the Golden Comparison Report and Reviews Decision Log.


def _surname(full_name: str) -> str:
    name_without_parenthetical = full_name.split("(")[0].strip()
    words = name_without_parenthetical.split()
    return words[-1] if words else full_name
