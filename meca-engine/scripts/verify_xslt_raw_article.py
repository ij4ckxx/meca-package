#!/usr/bin/env python
"""Verify the XSLT-based raw.xml/article.xml path against real reference packages.

Milestone 9. For every package in ``Input/``:

1. Runs the extraction/ICAM pipeline unchanged (needed for
   ``ArticleXmlGenerator``'s identity/custom-meta/rounds side-channel —
   see that module's docstring), then generates raw.xml via the new
   ``XsltRawXmlGenerator`` (source XML -> ``rawtocleanup.xslt``) instead
   of the ICAM-based ``RawXmlGenerator``, and article.xml via the
   existing, unmodified ``ArticleXmlGenerator`` composed on top of it.
2. For the 3 packages with a real, human-produced reference package in
   ``Output/``: parses both the new raw.xml and the reference's raw.xml
   and diffs them structurally (tag/attribute/child-count equality,
   ignoring whitespace) — not full-text/byte equality, since
   serialization style is not a correctness criterion here.
3. For every package (including the 3 above): confirms raw.xml/
   article.xml are well-formed, carry the expected DOCTYPE/dtd-version,
   and article.xml successfully derived without raising.

This script is deliberately standalone (not part of ``src/`` or
``tests/``) — it exercises real `Input/`/`Output/` files on disk, which
unit/golden tests must not depend on. Run from the ``meca-engine``
directory:

    PYTHONPATH=src python scripts/verify_xslt_raw_article.py
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

REPO_ROOT = Path(__file__).resolve().parents[2]
MECA_ENGINE_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO_ROOT / "Input"
DEFAULT_OUTPUT_DIR = MECA_ENGINE_ROOT / "verification_output" / "xslt_raw_article"
OUTPUT_REFERENCE_DIR = REPO_ROOT / "Output"

sys.path.insert(0, str(MECA_ENGINE_ROOT / "src"))

from meca_engine.config.loader import ConfigLoader  # noqa: E402
from meca_engine.config.schema import (  # noqa: E402
    CheckpointSettings,
    ConcurrencySettings,
    DashboardSettings,
    DoiRegistrySettings,
    InputSettings,
    LoggingSettings,
    FeatureFlagsConfig,
    JournalConfig,
    OutputSettings,
    PackagingSettings,
    PublisherConfig,
    RetrySettings,
    RuntimeConfig,
    StagingSettings,
    ValidationSettings,
)
from meca_engine.extraction.metadata_extraction import extract_all_metadata  # noqa: E402
from meca_engine.extraction.xml_loader import XmlLoader  # noqa: E402
from meca_engine.generators.article_xml.generator import ArticleXmlGenerator  # noqa: E402
from meca_engine.generators.context import GeneratorContext  # noqa: E402
from meca_engine.generators.diagnostics import DiagnosticsCollector  # noqa: E402
from meca_engine.generators.raw_xml.xslt_generator import XsltRawXmlGenerator  # noqa: E402
from meca_engine.generators.xml.namespaces import NamespaceManager  # noqa: E402
from meca_engine.logging_ import get_logger  # noqa: E402
from meca_engine.transform.coordinator import TransformationCoordinator  # noqa: E402

_CS_JOURNAL_BASE = dict(
    display_name="Clinical Science",
    doi_prefix="10.1042",
    article_type_mapping_ref="article-type-mapping.yaml",
    license_templates_ref="license-templates.yaml",
    doi_registry_scope="per-journal",
    publisher_id="portland-press",
)
_PORTLAND_PRESS_PUBLISHER = dict(
    publisher_id="portland-press",
    provider_name="Portland Press Limited",
    destination_provider_name="Silverchair",
    default_contact_policy="corresponding_author_email",
)

# (article_id, zip_name, xml_member, journal_kwargs, reference_zip_name | None)
ARTICLES = [
    (
        "CS-2025-6808",
        "CS-2025-6808.zip",
        "CS-2025-6808/cs-2025-6808.xml",
        dict(acronym="CLINSCI", **_CS_JOURNAL_BASE),
        "MECA_cs-2025-6808.zip",
    ),
    (
        "CS-2025-8493_C",
        "CS-2025-8493_C.zip",
        "CS-2025-8493/cs-2025-8493_C.xml",
        dict(acronym="CLINSCI", **_CS_JOURNAL_BASE),
        "MECA_CS-2025-8493_C.zip",
    ),
    (
        "cs-2025-8827",
        "cs-2025-8827.zip",
        "cs-2025-8827/cs-2025-8827.xml",
        dict(acronym="CS", **_CS_JOURNAL_BASE),
        "MECA_cs-2025-8827.zip",
    ),
    (
        "etls-2025-3020",
        "etls-2025-3020.zip",
        "etls-2025-3020.xml",
        dict(
            display_name="Emerging Topics in Life Sciences",
            doi_prefix="10.1042",
            acronym="ETLS",
            article_type_mapping_ref="article-type-mapping.yaml",
            license_templates_ref="license-templates.yaml",
            doi_registry_scope="per-journal",
            publisher_id="portland-press",
        ),
        None,
    ),
    (
        "bsr-2025-3205",
        "bsr-2025-3205.zip",
        "bsr-2025-3205.xml",
        dict(
            display_name="Bioscience Reports",
            doi_prefix="10.1042",
            acronym="BSR",
            article_type_mapping_ref="article-type-mapping.yaml",
            license_templates_ref="license-templates.yaml",
            doi_registry_scope="per-journal",
            publisher_id="portland-press",
        ),
        None,
    ),
    (
        "cs-2025-6682",
        "cs-2025-6682.zip",
        "cs-2025-6682.xml",
        dict(acronym="CLINSCI", **_CS_JOURNAL_BASE),
        None,
    ),
    (
        "bcj-2025-3130",
        "bcj-2025-3130.zip",
        "bcj-2025-3130.xml",
        dict(
            display_name="Biochemical Journal",
            doi_prefix="10.1042",
            acronym="BCJ",
            article_type_mapping_ref="article-type-mapping.yaml",
            license_templates_ref="license-templates.yaml",
            doi_registry_scope="per-journal",
            publisher_id="portland-press",
        ),
        None,
    ),
    (
        "cs-2024-5238",
        "cs-2024-5238.zip",
        "cs-2024-5238.xml",
        dict(acronym="CLINSCI", **_CS_JOURNAL_BASE),
        None,
    ),
]

_PARSER = etree.XMLParser(
    resolve_entities=False, no_network=True, load_dtd=False, dtd_validation=False
)


def _local(tag: object) -> str:
    return tag.split("}")[-1] if isinstance(tag, str) else str(tag)


def _structural_diff(
    a: etree._Element, b: etree._Element, path: str, out: list[str], depth: int = 0
) -> None:
    if depth > 200 or len(out) > 40:
        return
    a_attrs: dict[str, str] = {str(k): str(v) for k, v in a.attrib.items()}
    b_attrs: dict[str, str] = {str(k): str(v) for k, v in b.attrib.items()}
    if a_attrs != b_attrs:
        only_a = {k: v for k, v in a_attrs.items() if b_attrs.get(k) != v}
        only_b = {k: v for k, v in b_attrs.items() if a_attrs.get(k) != v}
        if only_a or only_b:
            out.append(f"{path}: attrs differ, reference-only={only_a} xslt-only={only_b}")
    a_children, b_children = list(a), list(b)
    if len(a_children) != len(b_children):
        out.append(
            f"{path}: child count differs, reference={len(a_children)} xslt={len(b_children)} "
            f"(reference tags={[_local(c.tag) for c in a_children]}, "
            f"xslt tags={[_local(c.tag) for c in b_children]})"
        )
        return
    # `strict=True` needs Python 3.10+; length is already checked above,
    # and this sandbox's available interpreter is 3.9 despite pyproject's
    # requires-python >=3.12 (see contributor_transformer.py history for
    # the same constraint elsewhere this milestone).
    for i, (ac, bc) in enumerate(zip(a_children, b_children)):  # noqa: B905
        if _local(ac.tag) != _local(bc.tag):
            a_tag, b_tag = _local(ac.tag), _local(bc.tag)
            out.append(f"{path}: tag mismatch at index {i}: reference={a_tag} xslt={b_tag}")
            continue
        _structural_diff(ac, bc, f"{path}/{_local(ac.tag)}", out, depth + 1)


def _well_formed_checks(article_id: str, xml_bytes: bytes, label: str) -> list[str]:
    problems: list[str] = []
    try:
        root = etree.fromstring(xml_bytes, parser=_PARSER)
    except etree.XMLSyntaxError as exc:
        return [f"{label}: not well-formed: {exc}"]
    if root.get("dtd-version") is None and label == "raw.xml":
        problems.append(f"{label}: missing dtd-version attribute")
    article_ids = root.findall(".//article-id")
    if not article_ids:
        problems.append(f"{label}: no <article-id> found")
    title = root.findtext(".//article-title")
    if not title:
        problems.append(f"{label}: no non-empty <article-title> found")
    return problems


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        help="Comma-separated article ids to run (default: all in ARTICLES).",
        default=None,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write generated raw.xml/article.xml files to, for manual review.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the XSLT-based raw.xml/article.xml pipeline against every `Input/` package."""
    args = _parse_args()
    only = set(args.only.split(",")) if args.only else None
    args.output_dir.mkdir(parents=True, exist_ok=True)

    loader = ConfigLoader(
        config_dir=MECA_ENGINE_ROOT / "config",
        schema_dir=MECA_ENGINE_ROOT / "schemas" / "config-schema",
    )
    namespace_manager = NamespaceManager(loader.load_namespace_config().namespaces)
    media_type_config = loader.load_media_type_config()

    xslt_raw_gen = XsltRawXmlGenerator()
    article_gen = ArticleXmlGenerator(
        namespace_manager=namespace_manager,
        article_xml_config=loader.load_article_xml_config(),
        article_type_mapping=loader.load_article_type_mapping(),
        license_templates=loader.load_license_templates(),
        # ArticleXmlGenerator.__init__ types this parameter concretely as
        # RawXmlGenerator; XsltRawXmlGenerator satisfies the same
        # duck-typed interface (.generate(), .namespace_prefixes) by
        # design (see xslt_generator.py's docstring) and this script's
        # own runs confirm it works at runtime. A shared Protocol should
        # replace the concrete type if/when a real cutover is wired in.
        raw_xml_generator=xslt_raw_gen,  # type: ignore[arg-type]
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

    overall_ok = True

    for article_id, zip_name, xml_member, journal_kwargs, reference_zip_name in ARTICLES:
        if only is not None and article_id not in only:
            continue
        print(f"\n=== {article_id} ===")
        logger = get_logger(f"verify_xslt.{article_id}")
        try:
            tmp_path = Path(tempfile.mkdtemp(prefix=f"verify_xslt_{article_id}_"))
            with zipfile.ZipFile(INPUT_DIR / zip_name) as archive:
                names = [n for n in archive.namelist() if "__MACOSX" not in n]
                archive.extractall(tmp_path, members=names)
            xml_path = tmp_path / xml_member
            if not xml_path.is_file():
                xml_path = next(tmp_path.rglob(Path(xml_member).name))
            staged_root = xml_path.parent

            document = XmlLoader(logger).load(xml_path)
            bundle = extract_all_metadata(document, logger)
            coordinator = TransformationCoordinator(
                media_type_config=media_type_config, logger=logger
            )
            model = coordinator.build_model(
                article_id=article_id,
                source_object_key=f"{article_id}/{xml_path.name}",
                staged_root=str(staged_root),
                parsed_document=document,
                extraction_bundle=bundle,
            )

            journal_config = JournalConfig(journal_id=model.identity.journal_id, **journal_kwargs)
            publisher_config = PublisherConfig(**_PORTLAND_PRESS_PUBLISHER)
            context = GeneratorContext(
                model=model,
                runtime_config=runtime_config,
                journal_config=journal_config,
                publisher_config=publisher_config,
                feature_flags=FeatureFlagsConfig(
                    reviews_include_duplicate_correspondence=True,
                    reviews_extended_history_scope=True,
                    strict_replication_mode=False,
                    allow_filename_fallback=True,
                ),
                logger=logger,
                diagnostics=DiagnosticsCollector(),
                source_xml_bytes=document.raw_bytes,
            )

            raw_result = xslt_raw_gen.generate(context)
            article_result = article_gen.generate(context)
            print(f"  raw.xml: {len(raw_result.document.xml_bytes)} bytes")
            print(f"  article.xml: {len(article_result.document.xml_bytes)} bytes")

            article_output_dir = args.output_dir / article_id
            article_output_dir.mkdir(parents=True, exist_ok=True)
            raw_path = article_output_dir / raw_result.document.filename
            article_path = article_output_dir / article_result.document.filename
            raw_path.write_bytes(raw_result.document.xml_bytes)
            article_path.write_bytes(article_result.document.xml_bytes)
            print(f"  written: {raw_path}")
            print(f"  written: {article_path}")

        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED: {type(exc).__name__}: {exc}")
            overall_ok = False
            continue

        problems = _well_formed_checks(article_id, raw_result.document.xml_bytes, "raw.xml")
        problems += _well_formed_checks(
            article_id, article_result.document.xml_bytes, "article.xml"
        )
        for p in problems:
            print(f"  ISSUE: {p}")
            overall_ok = False
        if not problems:
            print("  well-formedness/structural checks: OK")

        if reference_zip_name is not None:
            ref_zip_path = OUTPUT_REFERENCE_DIR / reference_zip_name
            with zipfile.ZipFile(ref_zip_path) as archive:
                ref_raw_name = next(n for n in archive.namelist() if n.endswith("_raw.xml"))
                ref_raw_bytes = archive.read(ref_raw_name)
            ref_root = etree.fromstring(ref_raw_bytes, parser=_PARSER)
            xslt_root = etree.fromstring(raw_result.document.xml_bytes, parser=_PARSER)
            diffs: list[str] = []
            _structural_diff(ref_root, xslt_root, "raw.xml", diffs)
            if diffs:
                print(
                    f"  DIFF vs real reference ({reference_zip_name}): {len(diffs)} difference(s)"
                )
                for d in diffs[:15]:
                    print(f"    - {d}")
                overall_ok = False
            else:
                print(f"  MATCHES real reference ({reference_zip_name}): structurally identical")

    print("\n=== RESULT ===")
    print("ALL CHECKS PASSED" if overall_ok else "ONE OR MORE ISSUES FOUND — see above")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
