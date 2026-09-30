"""Unit tests for meca_engine.packaging.builder.PackageBuilder.

Uses fake generators (rather than the real 5) so these tests isolate
`PackageBuilder`'s own orchestration logic — invocation order, atomicity,
DOI reservation, manifest-driven file resolution — from generator
business-rule correctness, which the golden tests already cover
end-to-end against the real generators.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from meca_engine.exceptions.article_errors import DoiCollisionError, PackageAssemblyError
from meca_engine.generators.result import GenerationResult
from meca_engine.logging_ import get_logger
from meca_engine.model.warnings import (
    ConfidenceLevel,
    EngineWarning,
    FindingOrigin,
    WarningCategory,
    WarningSeverity,
)
from meca_engine.packaging.asset_copy import AssetCopyService
from meca_engine.packaging.builder import PackageBuilder
from meca_engine.packaging.models import PackageStatus
from meca_engine.packaging.zip_builder import ZipBuilder
from meca_engine.registry.backends.in_memory import InMemoryDoiRegistry

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.generators.context import GeneratorContext
    from meca_engine.generators.xml.namespaces import NamespaceManager

pytestmark = pytest.mark.unit

_MANIFEST_URI = "https://manuscriptexchange.org/schema/manifest"
_XLINK_URI = "http://www.w3.org/1999/xlink"


@dataclass(frozen=True)
class _FakeDocument:
    article_id: str
    filename: str
    xml_bytes: bytes


class _FakeGenerator:
    """A minimal stand-in for a real ``BaseGenerator`` subclass."""

    def __init__(self, filename_suffix: str, xml_bytes: bytes) -> None:
        self.filename_suffix = filename_suffix
        self.xml_bytes = xml_bytes
        self.call_count = 0

    def generate(self, context: GeneratorContext) -> GenerationResult[_FakeDocument]:
        self.call_count += 1
        article_id = context.model.identity.article_id
        return GenerationResult(
            document=_FakeDocument(
                article_id=article_id,
                filename=f"{article_id}_{self.filename_suffix}.xml",
                xml_bytes=self.xml_bytes,
            ),
            generator_name=self.filename_suffix,
            article_id=article_id,
            duration_ms=0.1,
            diagnostics=(),
        )


class _RaisingGenerator:
    def generate(self, context: GeneratorContext) -> GenerationResult[_FakeDocument]:
        raise PackageAssemblyError("synthetic generator failure", retryable=False)


def _manifest_bytes(*, file_hrefs: tuple[str, ...] = ("files/R1/fig1.jpg",)) -> bytes:
    file_items = "".join(
        f'<item id="file-{i}" item-type="figure">'
        f'<instance media-type="image/jpeg" xlink:href="{href}"/></item>'
        for i, href in enumerate(file_hrefs, start=1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest xmlns="{_MANIFEST_URI}" xmlns:xlink="{_XLINK_URI}">
  <item id="item-article" item-type="article-metadata">
    <instance media-type="application/xml" xlink:href="placeholder_article.xml"/>
  </item>
  {file_items}
</manifest>""".encode()


def _article_bytes(doi: str = "10.1042/cs20250001") -> bytes:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<article><front><article-meta>
  <article-id pub-id-type="doi">{doi}</article-id>
</article-meta></front></article>""".encode()


class _RaisingZipBuilder:
    def build(self, *, source_root: Path, zip_path: Path, article_id: str) -> None:
        zip_path.write_bytes(b"partial, corrupt zip bytes")
        raise PackageAssemblyError("synthetic zip write failure", retryable=True)


class _RawOSErrorZipBuilder:
    """Simulates a disk-full/permission error — a raw, un-wrapped stdlib exception."""

    def build(self, *, source_root: Path, zip_path: Path, article_id: str) -> None:
        zip_path.write_bytes(b"partial, corrupt zip bytes")
        raise OSError("simulated disk-full while writing the zip")


def _builder(
    namespace_manager: NamespaceManager,
    *,
    manifest_bytes: bytes | None = None,
    article_bytes: bytes | None = None,
    doi_registry: InMemoryDoiRegistry | None = None,
    overwrite_policy: str = "fail",
    zip_builder: ZipBuilder | _RaisingZipBuilder | _RawOSErrorZipBuilder | None = None,
) -> tuple[PackageBuilder, dict[str, _FakeGenerator]]:
    logger = get_logger("test.package_builder")
    generators = {
        "raw": _FakeGenerator("raw", b"<raw/>"),
        "article": _FakeGenerator("article", article_bytes or _article_bytes()),
        "manifest": _FakeGenerator("manifest", manifest_bytes or _manifest_bytes()),
        "reviews": _FakeGenerator("reviews", b"<reviews/>"),
        "transfer": _FakeGenerator("transfer", b"<transfer/>"),
    }
    builder = PackageBuilder(
        raw_generator=generators["raw"],  # type: ignore[arg-type]
        article_generator=generators["article"],  # type: ignore[arg-type]
        manifest_generator=generators["manifest"],  # type: ignore[arg-type]
        reviews_generator=generators["reviews"],  # type: ignore[arg-type]
        transfer_generator=generators["transfer"],  # type: ignore[arg-type]
        namespace_manager=namespace_manager,
        asset_copy_service=AssetCopyService(overwrite_policy=overwrite_policy, logger=logger),
        zip_builder=zip_builder  # type: ignore[arg-type]
        or ZipBuilder(compression="deflated", compresslevel=6, logger=logger),
        logger=logger,
        doi_registry=doi_registry,
    )
    return builder, generators


def test_build_invokes_all_five_generators(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    builder, generators = _builder(namespace_manager)

    builder.build(context_with_resolved_file, output_root=tmp_path)

    assert all(generator.call_count == 1 for generator in generators.values())


def test_build_produces_a_zip_with_xml_and_asset_entries(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    builder, _ = _builder(namespace_manager)

    staged_package = builder.build(context_with_resolved_file, output_root=tmp_path)

    assert staged_package.zip_path.exists()
    with zipfile.ZipFile(staged_package.zip_path) as archive:
        names = set(archive.namelist())
        assert "files/R1/fig1.jpg" in names
        assert "CS-2025-0001_article.xml" in names
    assert len(staged_package.packaged_files) == 1
    assert staged_package.doi == "10.1042/cs20250001"


def _make_warning(
    *,
    code: str,
    category: WarningCategory,
    rule_id: str,
    recovery_rule_id: str | None,
    is_recovery: bool,
) -> EngineWarning:
    return EngineWarning(
        code=code,
        category=category,
        severity=WarningSeverity.WARNING,
        origin=FindingOrigin.SOURCE_DATA_ISSUE,
        rule_id=rule_id,
        recovery_rule_id=recovery_rule_id,
        confidence=ConfidenceLevel.MEDIUM,
        message="Test warning.",
        article_id="CS-2025-0001",
        suggested_action=None,
        is_recovery=is_recovery,
    )


def test_build_status_is_certified_when_model_has_no_warnings(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    builder, _ = _builder(namespace_manager)

    staged_package = builder.build(context_with_resolved_file, output_root=tmp_path)

    assert staged_package.status is PackageStatus.CERTIFIED
    assert staged_package.warnings == ()


def test_build_status_is_certified_with_warnings_when_model_has_advisory_warnings(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    warning = _make_warning(
        code="BR013_FALLBACK_FILENAME_FROM_PATH",
        category=WarningCategory.SPECIFICATION_FALLBACK,
        rule_id="BR-013",
        recovery_rule_id=None,
        is_recovery=False,
    )
    context = replace(
        context_with_resolved_file,
        model=replace(context_with_resolved_file.model, warnings=(warning,)),
    )
    builder, _ = _builder(namespace_manager)

    staged_package = builder.build(context, output_root=tmp_path)

    assert staged_package.status is PackageStatus.CERTIFIED_WITH_WARNINGS
    assert staged_package.warnings == (warning,)


def test_build_status_is_certified_with_recovery_when_a_lossless_recovery_fires(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    warning = _make_warning(
        code="BR013_FALLBACK_FILENAME_FROM_PATH",
        category=WarningCategory.SPECIFICATION_FALLBACK,
        rule_id="BR-013",
        recovery_rule_id="RR-001",
        is_recovery=True,
    )
    context = replace(
        context_with_resolved_file,
        model=replace(context_with_resolved_file.model, warnings=(warning,)),
    )
    builder, _ = _builder(namespace_manager)

    staged_package = builder.build(context, output_root=tmp_path)

    assert staged_package.status is PackageStatus.CERTIFIED_WITH_RECOVERY


def test_build_status_is_partial_certification_when_a_file_was_skipped(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    """RR-002 (missing file skipped) means real content is absent — a
    stronger signal than a lossless recovery like RR-001/RR-004/RR-005."""
    from dataclasses import replace

    warning = _make_warning(
        code="BR011_FILE_ENTRY_SKIPPED",
        category=WarningCategory.SOURCE_DATA_INCONSISTENCY,
        rule_id="BR-011",
        recovery_rule_id="RR-002",
        is_recovery=True,
    )
    context = replace(
        context_with_resolved_file,
        model=replace(context_with_resolved_file.model, warnings=(warning,)),
    )
    builder, _ = _builder(namespace_manager)

    staged_package = builder.build(context, output_root=tmp_path)

    assert staged_package.status is PackageStatus.PARTIAL_CERTIFICATION


def test_build_leaves_no_artifacts_when_a_generator_fails(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    builder, generators = _builder(namespace_manager)
    builder = PackageBuilder(
        raw_generator=generators["raw"],  # type: ignore[arg-type]
        article_generator=generators["article"],  # type: ignore[arg-type]
        manifest_generator=_RaisingGenerator(),  # type: ignore[arg-type]
        reviews_generator=generators["reviews"],  # type: ignore[arg-type]
        transfer_generator=generators["transfer"],  # type: ignore[arg-type]
        namespace_manager=namespace_manager,
        asset_copy_service=AssetCopyService(overwrite_policy="fail", logger=get_logger("t")),
        zip_builder=ZipBuilder(compression="deflated", compresslevel=6, logger=get_logger("t")),
        logger=get_logger("test.package_builder"),
    )

    with pytest.raises(PackageAssemblyError):
        builder.build(context_with_resolved_file, output_root=tmp_path)

    assert not any(tmp_path.glob("MECA_*.zip"))
    assert not any(tmp_path.glob(".package-staging-*"))
    assert not any(tmp_path.glob(".MECA_*.zip.tmp"))


def test_build_reserves_doi_when_registry_configured(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    registry = InMemoryDoiRegistry()
    builder, _ = _builder(namespace_manager, doi_registry=registry)

    builder.build(context_with_resolved_file, output_root=tmp_path)

    assert registry.is_reserved("10.1042/cs20250001") is True


def test_build_retry_after_a_later_failure_does_not_hit_its_own_doi_reservation(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    """A DOI reserved on a failed attempt must not block that same
    article's own redo-from-scratch retry (ADR-017)."""
    registry = InMemoryDoiRegistry()
    failing_builder, _ = _builder(
        namespace_manager, doi_registry=registry, zip_builder=_RaisingZipBuilder()
    )
    with pytest.raises(PackageAssemblyError):
        failing_builder.build(context_with_resolved_file, output_root=tmp_path)
    assert registry.is_reserved("10.1042/cs20250001") is True

    retry_builder, _ = _builder(namespace_manager, doi_registry=registry)
    staged_package = retry_builder.build(context_with_resolved_file, output_root=tmp_path)

    assert staged_package.doi == "10.1042/cs20250001"
    assert staged_package.zip_path.exists()


def test_build_raises_doi_collision_and_cleans_up(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    registry = InMemoryDoiRegistry()
    registry.reserve("10.1042/cs20250001", article_id="SOME-OTHER-ARTICLE")
    builder, _ = _builder(namespace_manager, doi_registry=registry)

    with pytest.raises(DoiCollisionError):
        builder.build(context_with_resolved_file, output_root=tmp_path)

    assert not any(tmp_path.glob("MECA_*.zip"))
    assert not any(tmp_path.glob(".package-staging-*"))
    assert not any(tmp_path.glob(".MECA_*.zip.tmp"))


def test_build_cleans_up_a_partially_written_zip_on_zip_failure(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    builder, _ = _builder(namespace_manager, zip_builder=_RaisingZipBuilder())

    with pytest.raises(PackageAssemblyError):
        builder.build(context_with_resolved_file, output_root=tmp_path)

    assert not any(tmp_path.glob("MECA_*.zip"))
    assert not any(tmp_path.glob(".package-staging-*"))
    assert not any(tmp_path.glob(".MECA_*.zip.tmp"))


def test_build_wraps_a_raw_exception_into_package_assembly_error(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    """Regression: a raw OSError (disk full, permission denied, ...) must never surface
    unclassified — it must be reported as PackageAssemblyError, per build()'s own contract."""
    builder, _ = _builder(namespace_manager, zip_builder=_RawOSErrorZipBuilder())

    with pytest.raises(PackageAssemblyError) as exc_info:
        builder.build(context_with_resolved_file, output_root=tmp_path)

    assert exc_info.value.inner_cause is not None
    assert isinstance(exc_info.value.inner_cause, OSError)
    assert not any(tmp_path.glob("MECA_*.zip"))
    assert not any(tmp_path.glob(".package-staging-*"))
    assert not any(tmp_path.glob(".MECA_*.zip.tmp"))


def test_build_raises_when_manifest_references_unresolvable_href(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    builder, _ = _builder(
        namespace_manager, manifest_bytes=_manifest_bytes(file_hrefs=("files/R1/missing.pdf",))
    )

    with pytest.raises(PackageAssemblyError):
        builder.build(context_with_resolved_file, output_root=tmp_path)

    assert not any(tmp_path.glob("MECA_*.zip"))
    assert not any(tmp_path.glob(".package-staging-*"))
    assert not any(tmp_path.glob(".MECA_*.zip.tmp"))


def test_build_with_no_doi_registry_still_returns_the_doi(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    builder, _ = _builder(namespace_manager, doi_registry=None)

    staged_package = builder.build(context_with_resolved_file, output_root=tmp_path)

    assert staged_package.doi == "10.1042/cs20250001"


def test_build_runs_configured_business_rule_hooks(
    namespace_manager: NamespaceManager,
    context_with_resolved_file: GeneratorContext,
    tmp_path: Path,
) -> None:
    from meca_engine.generators.validation_hooks import ValidationIssue, ValidationIssueSeverity

    calls: list[str] = []

    class _RecordingHook:
        def validate(self, document: bytes, *, generator_name: str) -> tuple[ValidationIssue, ...]:
            calls.append(generator_name)
            return (ValidationIssue(severity=ValidationIssueSeverity.INFO, message="ok"),)

    logger = get_logger("test.package_builder")
    generators = {
        "raw": _FakeGenerator("raw", b"<raw/>"),
        "article": _FakeGenerator("article", _article_bytes()),
        "manifest": _FakeGenerator("manifest", _manifest_bytes()),
        "reviews": _FakeGenerator("reviews", b"<reviews/>"),
        "transfer": _FakeGenerator("transfer", b"<transfer/>"),
    }
    builder = PackageBuilder(
        raw_generator=generators["raw"],  # type: ignore[arg-type]
        article_generator=generators["article"],  # type: ignore[arg-type]
        manifest_generator=generators["manifest"],  # type: ignore[arg-type]
        reviews_generator=generators["reviews"],  # type: ignore[arg-type]
        transfer_generator=generators["transfer"],  # type: ignore[arg-type]
        namespace_manager=namespace_manager,
        asset_copy_service=AssetCopyService(overwrite_policy="fail", logger=logger),
        zip_builder=ZipBuilder(compression="deflated", compresslevel=6, logger=logger),
        logger=logger,
        business_rule_hooks=(_RecordingHook(),),  # type: ignore[arg-type]
    )

    builder.build(context_with_resolved_file, output_root=tmp_path)

    assert calls == ["raw", "article", "manifest", "reviews", "transfer"]
