"""Shared fixtures for Package Assembly unit tests."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import TYPE_CHECKING

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
from meca_engine.generators.xml.namespaces import NamespaceManager
from meca_engine.logging_ import get_logger
from meca_engine.model.article import ArticleModel, ResolvedFile
from tests.unit.generators.conftest import build_minimal_article_model

if TYPE_CHECKING:
    from pathlib import Path

_MANIFEST_URI = "https://manuscriptexchange.org/schema/manifest"
_XLINK_URI = "http://www.w3.org/1999/xlink"


@pytest.fixture
def namespace_manager() -> NamespaceManager:
    return NamespaceManager({"meca-manifest": _MANIFEST_URI, "xlink": _XLINK_URI})


@pytest.fixture
def resolved_file(tmp_path: Path) -> ResolvedFile:
    source_dir = tmp_path / "sources"
    source_dir.mkdir(exist_ok=True)
    source_path = source_dir / "fig1.jpg"
    content = b"figure bytes"
    source_path.write_bytes(content)

    return ResolvedFile(
        round_label="R1",
        category="figure",
        original_filename="fig1.jpg",
        staged_physical_path=str(source_path),
        checksum=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        media_type="image/jpeg",
    )


def _build_context(model: ArticleModel) -> GeneratorContext:
    return GeneratorContext(
        model=model,
        runtime_config=RuntimeConfig(
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
        ),
        journal_config=JournalConfig(
            journal_id="clinical-science",
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
        logger=get_logger("test.packaging"),
        diagnostics=DiagnosticsCollector(),
    )


@pytest.fixture
def generator_context() -> GeneratorContext:
    return _build_context(build_minimal_article_model("CS-2025-0001"))


@pytest.fixture
def context_with_resolved_file(resolved_file: ResolvedFile) -> GeneratorContext:
    model = replace(build_minimal_article_model("CS-2025-0001"), resolved_files=(resolved_file,))
    return _build_context(model)
