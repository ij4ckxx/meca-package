"""Package Builder — the single orchestration point for Package Assembly (Milestone 7).

Per the task's explicit constraint, this module contains **no business
logic**: every XML byte comes from the 5 existing generators
(unmodified), the file list comes from manifest.xml
(:mod:`meca_engine.packaging.document_reader`), and the DOI comes from
article.xml (same module) — this class only sequences those already-made
decisions into one atomic, on-disk package.

Atomicity (ADR-017): everything is assembled under a hidden, per-article
staging directory and a hidden temporary zip path; the real
``MECA_<ArticleID>.zip`` only comes into existence via one atomic
``os.replace`` after every prior step has succeeded. Any exception at any
point triggers cleanup of both temporary paths before propagating, so no
partial package is ever left at the published location.
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING

from meca_engine.exceptions import MecaEngineError
from meca_engine.exceptions.article_errors import DoiCollisionError, PackageAssemblyError
from meca_engine.model.recovery_rules import SIGNIFICANT_DEFICIENCY_RULE_IDS
from meca_engine.packaging.document_reader import extract_generated_doi, extract_packaged_file_hrefs
from meca_engine.packaging.models import (
    GeneratedDocumentSet,
    PackagedFile,
    PackageStatus,
    StagedPackage,
)

if TYPE_CHECKING:
    from meca_engine.generators.article_xml.generator import ArticleXmlGenerator
    from meca_engine.generators.context import GeneratorContext
    from meca_engine.generators.diagnostics import GeneratorDiagnostic
    from meca_engine.generators.manifest_xml.generator import ManifestXmlGenerator
    from meca_engine.generators.raw_xml.generator import RawXmlGenerator
    from meca_engine.generators.reviews_xml.generator import ReviewsXmlGenerator
    from meca_engine.generators.transfer_xml.generator import TransferXmlGenerator
    from meca_engine.generators.validation_hooks import BusinessRuleValidationHook
    from meca_engine.generators.xml.namespaces import NamespaceManager
    from meca_engine.logging_.structured_logger import StructuredLogger
    from meca_engine.model.article import ResolvedFile
    from meca_engine.model.warnings import EngineWarning
    from meca_engine.packaging.asset_copy import AssetCopyService
    from meca_engine.packaging.zip_builder import ZipBuilder
    from meca_engine.registry.doi_registry import DoiRegistry

_STAGE = "meca_engine.packaging.builder"


def _expected_href(resolved_file: ResolvedFile) -> str:
    """The href manifest.xml's own BR-082 convention assigns this file."""
    filename = Path(resolved_file.staged_physical_path).name
    return f"files/{resolved_file.round_label}/{filename}"


class PackageBuilder:
    """Assembles one article's complete MECA package.

    Stateless by contract, mirroring
    :class:`meca_engine.generators.base.BaseGenerator`: holds only
    injected, read-only collaborators, so one instance is safely reusable
    across every article in a batch (13_LLD_04 §9's concurrency/reuse
    expectations).
    """

    def __init__(
        self,
        *,
        raw_generator: RawXmlGenerator,
        article_generator: ArticleXmlGenerator,
        manifest_generator: ManifestXmlGenerator,
        reviews_generator: ReviewsXmlGenerator,
        transfer_generator: TransferXmlGenerator,
        namespace_manager: NamespaceManager,
        asset_copy_service: AssetCopyService,
        zip_builder: ZipBuilder,
        logger: StructuredLogger,
        doi_registry: DoiRegistry | None = None,
        business_rule_hooks: tuple[BusinessRuleValidationHook, ...] = (),
    ) -> None:
        """Initialize the Package Builder.

        Args:
            raw_generator: Already-configured raw.xml generator.
            article_generator: Already-configured article.xml generator.
            manifest_generator: Already-configured manifest.xml generator.
            reviews_generator: Already-configured reviews.xml generator.
            transfer_generator: Already-configured transfer.xml generator.
            namespace_manager: Reused to parse the generated manifest.xml
                back (:mod:`meca_engine.packaging.document_reader`).
            asset_copy_service: Copies physical assets into the package.
            zip_builder: Produces the final archive.
            logger: Structured logger for lifecycle events.
            doi_registry: Optional DOI uniqueness validator (BR-154). If
                ``None``, no uniqueness check is performed — the caller
                is responsible for deciding whether that is acceptable
                for its deployment.
            business_rule_hooks: Optional, already-implemented
                :class:`~meca_engine.generators.validation_hooks.BusinessRuleValidationHook`
                instances to run against each generated document. Empty
                by default, since no concrete hook implementation exists
                yet (Milestone 6A's validation extension points remain
                reserved for the future Validation Engine milestone).
        """
        self._raw_generator = raw_generator
        self._article_generator = article_generator
        self._manifest_generator = manifest_generator
        self._reviews_generator = reviews_generator
        self._transfer_generator = transfer_generator
        self._namespace_manager = namespace_manager
        self._asset_copy_service = asset_copy_service
        self._zip_builder = zip_builder
        self._logger = logger
        self._doi_registry = doi_registry
        self._business_rule_hooks = business_rule_hooks

    def build(self, context: GeneratorContext, *, output_root: Path) -> StagedPackage:
        """Generate, validate, and assemble one article's complete MECA package.

        Args:
            context: The fully-populated generation context (ICAM +
                config + diagnostics) shared by all 5 generators.
            output_root: Directory the final ``MECA_<ArticleID>.zip`` is
                written into; also the parent of this build's temporary
                staging directory.

        Returns:
            The completed :class:`~meca_engine.packaging.models.StagedPackage`.

        Raises:
            MecaEngineError: Propagated unchanged from any of the 5
                generators (a business-rule or code-defect failure stops
                assembly entirely — no partial package is produced).
            DoiCollisionError: If a DOI Registry is configured and the
                generated DOI is already reserved by another article.
            PackageAssemblyError: On any asset-copy or zip-write failure.
        """
        article_id = context.model.identity.article_id
        start = time.perf_counter()
        self._logger.info("package start", stage=_STAGE, context={"article_id": article_id})

        staging_dir = output_root / f".package-staging-{article_id}"
        zip_tmp_path = output_root / f".MECA_{article_id}.zip.tmp"
        zip_final_path = output_root / f"MECA_{article_id}.zip"

        try:
            documents = self._generate_all(context)
            self._run_validation_hooks(documents, article_id=article_id)
            packaged_files = self._resolve_packaged_files(
                context, documents.manifest.document.xml_bytes
            )
            doi = self._reserve_doi(documents.article.document.xml_bytes, article_id=article_id)

            shutil.rmtree(staging_dir, ignore_errors=True)
            staging_dir.mkdir(parents=True)
            xml_filenames = self._write_xml_documents(documents, staging_dir)
            self._asset_copy_service.copy_all(
                packaged_files, destination_root=staging_dir, article_id=article_id
            )

            zip_tmp_path.unlink(missing_ok=True)
            self._zip_builder.build(
                source_root=staging_dir, zip_path=zip_tmp_path, article_id=article_id
            )
            os.replace(zip_tmp_path, zip_final_path)
        except BaseException as exc:
            shutil.rmtree(staging_dir, ignore_errors=True)
            if zip_tmp_path.exists():
                zip_tmp_path.unlink(missing_ok=True)
            duration_ms = (time.perf_counter() - start) * 1000.0
            self._logger.error(
                "package failed",
                stage=_STAGE,
                context={"article_id": article_id, "duration_ms": duration_ms},
            )
            # Every raw asset-copy/zip-write failure (disk full, permission
            # denied, ...) is wrapped here so it is never reported as an
            # unclassified exception downstream — matches this method's own
            # documented `Raises: PackageAssemblyError` contract, which a
            # bare `OSError` previously bypassed. `MecaEngineError`s (a
            # generator's own failure, a DOI collision) are propagated
            # unchanged, as documented; `KeyboardInterrupt`/`SystemExit`
            # are never wrapped, so an operator can still stop a run cleanly.
            if isinstance(exc, Exception) and not isinstance(exc, MecaEngineError):
                raise PackageAssemblyError(
                    f"Package assembly failed for {article_id!r}: {exc}",
                    retryable=False,
                    article_id=article_id,
                    stage=_STAGE,
                    inner_cause=exc,
                ) from exc
            raise
        else:
            shutil.rmtree(staging_dir, ignore_errors=True)

        duration_ms = (time.perf_counter() - start) * 1000.0
        self._logger.performance(
            f"Package assembly for {article_id!r} completed in {duration_ms:.2f}ms",
            duration_ms=duration_ms,
            stage=_STAGE,
            context={"article_id": article_id},
        )
        self._logger.info(
            "package complete",
            stage=_STAGE,
            context={"article_id": article_id, "zip_path": str(zip_final_path)},
        )
        warnings = context.model.warnings
        generator_diagnostics = context.diagnostics.diagnostics
        return StagedPackage(
            article_id=article_id,
            zip_path=zip_final_path,
            doi=doi,
            packaged_files=packaged_files,
            xml_filenames=xml_filenames,
            status=_compute_status(warnings, generator_diagnostics),
            warnings=warnings,
            generator_diagnostics=generator_diagnostics,
        )

    def _generate_all(self, context: GeneratorContext) -> GeneratedDocumentSet:
        return GeneratedDocumentSet(
            raw=self._raw_generator.generate(context),
            article=self._article_generator.generate(context),
            manifest=self._manifest_generator.generate(context),
            reviews=self._reviews_generator.generate(context),
            transfer=self._transfer_generator.generate(context),
        )

    def _run_validation_hooks(self, documents: GeneratedDocumentSet, *, article_id: str) -> None:
        if not self._business_rule_hooks:
            return
        issue_count = 0
        for result in (
            documents.raw,
            documents.article,
            documents.manifest,
            documents.reviews,
            documents.transfer,
        ):
            for hook in self._business_rule_hooks:
                issue_count += len(
                    hook.validate(result.document.xml_bytes, generator_name=result.generator_name)
                )
        self._logger.info(
            "validation summary",
            stage=_STAGE,
            context={"article_id": article_id, "issue_count": issue_count},
        )

    def _resolve_packaged_files(
        self, context: GeneratorContext, manifest_xml_bytes: bytes
    ) -> tuple[PackagedFile, ...]:
        hrefs = extract_packaged_file_hrefs(manifest_xml_bytes, self._namespace_manager)
        resolved_by_href = {
            _expected_href(resolved_file): resolved_file
            for resolved_file in context.model.resolved_files
        }
        article_id = context.model.identity.article_id
        packaged_files: list[PackagedFile] = []
        for href in hrefs:
            resolved_file = resolved_by_href.get(href)
            if resolved_file is None:
                raise PackageAssemblyError(
                    f"manifest.xml references href {href!r} with no matching resolved file",
                    retryable=False,
                    article_id=article_id,
                    stage=_STAGE,
                    rule_id="BR-152",
                )
            packaged_files.append(
                PackagedFile(
                    href=href,
                    source_path=Path(resolved_file.staged_physical_path),
                    checksum=resolved_file.checksum,
                    size_bytes=resolved_file.size_bytes,
                )
            )
        return tuple(packaged_files)

    def _reserve_doi(self, article_xml_bytes: bytes, *, article_id: str) -> str | None:
        doi = extract_generated_doi(article_xml_bytes)
        if doi is None or self._doi_registry is None:
            return doi
        if not self._doi_registry.reserve(doi, article_id=article_id):
            raise DoiCollisionError(
                f"DOI {doi!r} is already reserved by another article",
                article_id=article_id,
                stage=_STAGE,
                rule_id="BR-154",
            )
        return doi

    @staticmethod
    def _write_xml_documents(documents: GeneratedDocumentSet, staging_dir: Path) -> tuple[str, ...]:
        filenames: list[str] = []
        for result in (
            documents.raw,
            documents.article,
            documents.manifest,
            documents.reviews,
            documents.transfer,
        ):
            (staging_dir / result.document.filename).write_bytes(result.document.xml_bytes)
            filenames.append(result.document.filename)
        return tuple(filenames)


def _compute_status(
    warnings: tuple[EngineWarning, ...],
    generator_diagnostics: tuple[GeneratorDiagnostic, ...],
) -> PackageStatus:
    """Milestone 12 (ADR-034): derive this build's :class:`PackageStatus`.

    ``PARTIAL_CERTIFICATION`` whenever a significant-deficiency Recovery
    Rule fired (currently only RR-002 — a declared file could not be
    recovered and was skipped, see `model/recovery_rules.py`);
    ``CERTIFIED_WITH_RECOVERY`` whenever any other recovery fired
    (``is_recovery=True`` with no lost content); ``CERTIFIED_WITH_WARNINGS``
    if any warning or generator diagnostic exists at all without a
    recovery; ``CERTIFIED`` otherwise. A build that could not complete
    never reaches this function — it raised instead (see
    :class:`PackageStatus`'s own docstring).
    """
    recoveries = [warning for warning in warnings if warning.is_recovery]
    if any(warning.recovery_rule_id in SIGNIFICANT_DEFICIENCY_RULE_IDS for warning in recoveries):
        return PackageStatus.PARTIAL_CERTIFICATION
    if recoveries:
        return PackageStatus.CERTIFIED_WITH_RECOVERY
    if warnings or generator_diagnostics:
        return PackageStatus.CERTIFIED_WITH_WARNINGS
    return PackageStatus.CERTIFIED
