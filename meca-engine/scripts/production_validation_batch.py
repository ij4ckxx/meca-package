#!/usr/bin/env python
"""Production Validation batch runner — all Input/ packages, full pipeline.

Runs the complete, current-state engine (Milestone 9's XSLT-based raw.xml,
Milestone 10's warning-based fallback, all 5 generators, full
PackageBuilder assembly) against every package in ``Input/``, continuing
past any individual failure. Successful packages are written to
``production_validation/generated_packages/`` — deliberately NOT
``Output/``, which holds this project's 3 real, human-authored reference
packages and must never be overwritten.

Writes a structured JSON execution log
(``production_validation/batch_execution_log.json``) that every
production-validation report is derived from, so the pipeline need not be
re-run per report.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MECA_ENGINE_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO_ROOT / "Input"
OUTPUT_DIR = REPO_ROOT / "production_validation" / "generated_packages"
LOG_PATH = REPO_ROOT / "production_validation" / "batch_execution_log.json"

sys.path.insert(0, str(MECA_ENGINE_ROOT / "src"))

from meca_engine.config.loader import ConfigLoader  # noqa: E402
from meca_engine.config.schema import (  # noqa: E402
    CheckpointSettings,
    ConcurrencySettings,
    DashboardSettings,
    DoiRegistrySettings,
    InputSettings,
    LoggingSettings,
    JournalConfig,
    OutputSettings,
    PackagingSettings,
    PublisherConfig,
    RetrySettings,
    RuntimeConfig,
    StagingSettings,
    ValidationSettings,
)
from meca_engine.exceptions import MecaEngineError  # noqa: E402
from meca_engine.extraction.metadata_extraction import extract_all_metadata  # noqa: E402
from meca_engine.extraction.xml_loader import XmlLoader  # noqa: E402
from meca_engine.generators.article_xml.generator import ArticleXmlGenerator  # noqa: E402
from meca_engine.generators.context import GeneratorContext  # noqa: E402
from meca_engine.generators.diagnostics import DiagnosticsCollector  # noqa: E402
from meca_engine.generators.manifest_xml.generator import ManifestXmlGenerator  # noqa: E402
from meca_engine.generators.raw_xml.xslt_generator import XsltRawXmlGenerator  # noqa: E402
from meca_engine.generators.reviews_xml.generator import ReviewsXmlGenerator  # noqa: E402
from meca_engine.generators.transfer_xml.generator import TransferXmlGenerator  # noqa: E402
from meca_engine.generators.xml.namespaces import NamespaceManager  # noqa: E402
from meca_engine.logging_ import get_logger  # noqa: E402
from meca_engine.packaging.asset_copy import AssetCopyService  # noqa: E402
from meca_engine.packaging.builder import PackageBuilder  # noqa: E402
from meca_engine.packaging.zip_builder import ZipBuilder  # noqa: E402
from meca_engine.registry.backends.in_memory import InMemoryDoiRegistry  # noqa: E402
from meca_engine.transform.coordinator import TransformationCoordinator  # noqa: E402

# Real journal identity, read directly from each journal's own source XML
# (journal-id/publisher-id) during this session's investigation — never
# fabricated. `acronym` follows the same, already-validated ADR-007
# fallback pattern confirmed correct for bcj/bsr in prior certification
# rounds: uppercase the journal's own publisher-id when no ADR-007
# business override exists. Only Clinical Science (CS/cs) has a
# confirmed, non-derivable override (`CLINSCI` for 2 of 3 golden
# samples, `CS` for the third) — see ADR-007.
_JOURNAL_CONFIG_BY_PREFIX = {
    "CS": dict(display_name="Clinical Science", acronym="CLINSCI"),
    "cs": dict(display_name="Clinical Science", acronym="CLINSCI"),
    "bcj": dict(display_name="Biochemical Journal", acronym="BCJ"),
    "bsr": dict(display_name="Bioscience Reports", acronym="BSR"),
    "bst": dict(display_name="Biochemical Society Transactions", acronym="BST"),
    "ebc": dict(display_name="Essays in Biochemistry", acronym="EBC"),
    "etls": dict(display_name="Emerging Topics in Life Sciences", acronym="ETLS"),
}
# cs-2025-8827's real source has abbrev-type="publisher"="CS" — the one
# confirmed exception to the CLINSCI default (established in prior
# certification rounds via direct source inspection).
_ACRONYM_OVERRIDE_BY_ARTICLE_ID = {"cs-2025-8827": "CS"}

_PORTLAND_PRESS_PUBLISHER = dict(
    publisher_id="portland-press",
    provider_name="Portland Press Limited",
    destination_provider_name="Silverchair",
    default_contact_policy="corresponding_author_email",
)


def _journal_prefix(article_id: str) -> str:
    prefix = []
    for ch in article_id:
        if ch.isalpha():
            prefix.append(ch)
        else:
            break
    return "".join(prefix)


def _find_source_xml(extracted_root: Path, article_id: str) -> Path:
    candidates = [
        p
        for p in extracted_root.rglob("*.xml")
        if "__MACOSX" not in p.parts and not p.name.startswith("._")
    ]
    if not candidates:
        raise FileNotFoundError(f"No source XML found for {article_id!r} under {extracted_root}")
    if len(candidates) == 1:
        return candidates[0]
    # Prefer an exact article-id-shaped filename when more than one XML exists.
    for p in candidates:
        if p.stem.lower() == article_id.lower():
            return p
    return candidates[0]


def main() -> int:
    """Run the full pipeline against every Input/ package, continuing past failures."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    loader = ConfigLoader(
        config_dir=MECA_ENGINE_ROOT / "config",
        schema_dir=MECA_ENGINE_ROOT / "schemas" / "config-schema",
    )
    namespace_manager = NamespaceManager(loader.load_namespace_config().namespaces)
    media_type_config = loader.load_media_type_config()
    feature_flags = loader.load_feature_flags()

    raw_gen = XsltRawXmlGenerator()
    article_gen = ArticleXmlGenerator(
        namespace_manager=namespace_manager,
        article_xml_config=loader.load_article_xml_config(),
        article_type_mapping=loader.load_article_type_mapping(),
        license_templates=loader.load_license_templates(),
        raw_xml_generator=raw_gen,  # type: ignore[arg-type]
    )
    manifest_gen = ManifestXmlGenerator(
        namespace_manager=namespace_manager,
        manifest_xml_config=loader.load_manifest_xml_config(),
        item_type_mapping=loader.load_item_type_mapping(),
        media_type_config=media_type_config,
    )
    reviews_gen = ReviewsXmlGenerator(
        namespace_manager=namespace_manager, reviews_xml_config=loader.load_reviews_xml_config()
    )
    transfer_gen = TransferXmlGenerator(
        namespace_manager=namespace_manager, transfer_xml_config=loader.load_transfer_xml_config()
    )

    runtime_config = RuntimeConfig(
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
    publisher_config = PublisherConfig(**_PORTLAND_PRESS_PUBLISHER)
    shared_doi_registry = InMemoryDoiRegistry()

    package_builder = PackageBuilder(
        raw_generator=raw_gen,  # type: ignore[arg-type]
        article_generator=article_gen,
        manifest_generator=manifest_gen,
        reviews_generator=reviews_gen,
        transfer_generator=transfer_gen,
        namespace_manager=namespace_manager,
        asset_copy_service=AssetCopyService(
            overwrite_policy="fail", logger=get_logger("pv.assets")
        ),
        zip_builder=ZipBuilder(
            compression="deflated", compresslevel=6, logger=get_logger("pv.zip")
        ),
        logger=get_logger("pv.builder"),
        doi_registry=shared_doi_registry,
    )

    results: list[dict[str, object]] = []
    zip_paths = sorted(INPUT_DIR.glob("*.zip"))
    print(f"Found {len(zip_paths)} packages in {INPUT_DIR}")

    for zip_path in zip_paths:
        article_id = zip_path.stem
        prefix = _journal_prefix(article_id)
        entry: dict[str, object] = {"article_id": article_id, "journal_prefix": prefix}
        logger = get_logger(f"pv.{article_id}")
        stage = "input"
        t_start = time.perf_counter()
        try:
            import tempfile

            tmp_path = Path(tempfile.mkdtemp(prefix=f"pv_{article_id}_"))
            with zipfile.ZipFile(zip_path) as archive:
                names = [n for n in archive.namelist() if "__MACOSX" not in n]
                archive.extractall(tmp_path, members=names)

            stage = "discover_source_xml"
            xml_path = _find_source_xml(tmp_path, article_id)
            staged_root = xml_path.parent
            entry["physical_file_count"] = sum(
                1 for p in staged_root.rglob("*") if p.is_file() and p != xml_path
            )

            stage = "parse"
            document = XmlLoader(logger).load(xml_path)

            stage = "extract"
            bundle = extract_all_metadata(document, logger)
            entry["extraction_diagnostics_count"] = len(bundle.diagnostics)

            stage = "transform"
            coordinator = TransformationCoordinator(
                media_type_config=media_type_config, logger=logger, feature_flags=feature_flags
            )
            model = coordinator.build_model(
                article_id=article_id,
                source_object_key=f"{article_id}/{xml_path.name}",
                staged_root=str(staged_root),
                parsed_document=document,
                extraction_bundle=bundle,
            )
            entry["resolved_files_count"] = len(model.resolved_files)
            entry["rounds"] = [(r.label, r.sequence_number, r.is_latest) for r in model.rounds]
            entry["warnings"] = [
                {
                    "code": w.code,
                    "category": w.category.value,
                    "severity": w.severity.value,
                    "rule_id": w.rule_id,
                    "message": w.message,
                    "context": dict(w.context),
                }
                for w in model.warnings
            ]

            journal_defaults = _JOURNAL_CONFIG_BY_PREFIX.get(prefix)
            if journal_defaults is None:
                raise ValueError(f"No journal config mapping for prefix {prefix!r}")
            acronym = _ACRONYM_OVERRIDE_BY_ARTICLE_ID.get(article_id, journal_defaults["acronym"])
            journal_config = JournalConfig(
                journal_id=model.identity.journal_id,
                display_name=journal_defaults["display_name"],
                doi_prefix="10.1042",
                acronym=acronym,
                article_type_mapping_ref="article-type-mapping.yaml",
                license_templates_ref="license-templates.yaml",
                doi_registry_scope="per-journal",
                publisher_id="portland-press",
            )

            stage = "generate+package"
            diagnostics = DiagnosticsCollector()
            context = GeneratorContext(
                model=model,
                runtime_config=runtime_config,
                journal_config=journal_config,
                publisher_config=publisher_config,
                feature_flags=feature_flags,
                logger=logger,
                diagnostics=diagnostics,
                source_xml_bytes=document.raw_bytes,
            )
            article_output_root = OUTPUT_DIR / article_id
            article_output_root.mkdir(parents=True, exist_ok=True)
            staged_package = package_builder.build(context, output_root=article_output_root)

            entry["status"] = staged_package.status.value
            entry["zip_path"] = str(staged_package.zip_path)
            entry["doi"] = staged_package.doi
            entry["xml_filenames"] = list(staged_package.xml_filenames)
            entry["packaged_files_count"] = len(staged_package.packaged_files)
            entry["generator_diagnostics_count"] = len(diagnostics.diagnostics)
            entry["generator_diagnostics"] = [
                {"severity": d.severity.value, "message": d.message, "generator": d.generator_name}
                for d in diagnostics.diagnostics
            ]
            entry["warnings_count"] = len(entry["warnings"])  # type: ignore[arg-type]

        except MecaEngineError as exc:
            entry["status"] = "FAIL"
            entry["failed_stage"] = stage
            entry["error_type"] = type(exc).__name__
            entry["error_message"] = str(exc)
            entry["rule_id"] = getattr(exc, "rule_id", None)
        except Exception as exc:  # noqa: BLE001
            entry["status"] = "FAIL"
            entry["failed_stage"] = stage
            entry["error_type"] = type(exc).__name__
            entry["error_message"] = str(exc)
            entry["traceback"] = traceback.format_exc()

        entry["elapsed_seconds"] = round(time.perf_counter() - t_start, 3)
        results.append(entry)
        status = entry.get("status", "UNKNOWN")
        print(f"{article_id}: {status} ({entry['elapsed_seconds']}s)", flush=True)

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "w") as fh:
        json.dump(results, fh, indent=2, default=str)

    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "pass")
    passed_warn = sum(1 for r in results if r.get("status") == "pass_with_warnings")
    failed = sum(1 for r in results if r.get("status") == "FAIL")
    print("\n=== SUMMARY ===")
    print(f"Total: {total}  PASS: {passed}  PASS_WITH_WARNINGS: {passed_warn}  FAIL: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
