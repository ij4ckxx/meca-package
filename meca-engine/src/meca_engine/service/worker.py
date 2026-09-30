"""Worker — processes one Job through the existing, unchanged conversion pipeline.

Reuses every existing stage unchanged: :class:`~meca_engine.extraction.xml_loader.XmlLoader`,
:func:`~meca_engine.extraction.metadata_extraction.extract_all_metadata`,
:class:`~meca_engine.transform.coordinator.TransformationCoordinator`,
:class:`~meca_engine.generators.context.GeneratorContext`, and
:class:`~meca_engine.packaging.batch_runner.PackageBatchRunner` (which itself
drives :class:`~meca_engine.packaging.builder.PackageBuilder` with checkpoint-
based claim/skip/resume). The Worker's only new responsibility is operational
resilience: wrapping the whole per-article attempt in
:func:`meca_engine.retry.run_with_retry` so a transient infrastructure failure
(temporary I/O, a dropped connection, a momentarily unavailable DOI Registry
or Checkpoint Store) is retried, while a deterministic conversion failure
(a Business Rule violation, a missing source file, malformed metadata, an
XML error) never is — see :mod:`meca_engine.retry` for that classification.
"""

from __future__ import annotations

import dataclasses
import shutil
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from meca_engine.config.schema import JournalConfig
from meca_engine.exceptions import (
    MecaEngineError,
    ModelBuildError,
    PackageAssemblyError,
)
from meca_engine.exceptions.article_errors import (
    ArticleTransientError,
    GeneratorInvariantError,
    XmlSerializationError,
)
from meca_engine.extraction.metadata_extraction import extract_all_metadata
from meca_engine.extraction.xml_loader import XmlLoader
from meca_engine.generators.context import GeneratorContext
from meca_engine.generators.diagnostics import DiagnosticsCollector
from meca_engine.logging_ import get_logger
from meca_engine.packaging.batch_runner import PackageOutcomeStatus
from meca_engine.packaging.conversion_report import build_conversion_report
from meca_engine.packaging.models import PackageStatus
from meca_engine.reporting.certification_report import write_certification_report
from meca_engine.reporting.migration_audit import (
    write_migration_audit_json,
    write_migration_audit_report,
)
from meca_engine.reporting.package_embed import embed_conversion_report
from meca_engine.reporting.reproducibility import (
    build_reproducibility_info,
    compute_config_checksum,
)
from meca_engine.reporting.transformation_summary import write_transformation_summary
from meca_engine.reporting.validation_report import write_validation_report
from meca_engine.retry import run_with_retry
from meca_engine.service.job import JobStatus
from meca_engine.transform.coordinator import TransformationCoordinator
from meca_engine.validation import validate_staged_package

if TYPE_CHECKING:
    from meca_engine.config.schema import (
        FeatureFlagsConfig,
        MediaTypeConfig,
        PublisherConfig,
        RetrySettings,
        RuntimeConfig,
    )
    from meca_engine.logging_.structured_logger import StructuredLogger
    from meca_engine.packaging.batch_runner import PackageBatchRunner
    from meca_engine.packaging.conversion_report import ConversionReport
    from meca_engine.providers.input import InputProvider, StagedArticle
    from meca_engine.providers.output import OutputProvider
    from meca_engine.service.job import Job
    from meca_engine.service.router import OutputRouter

_STAGE = "meca_engine.service.worker"

# Same journal identity table as the pre-Phase-1 batch script — real,
# non-fabricated publisher-provided data, unchanged by this refactor.
# Keys are normalized (lowercase) once at lookup time by
# `_journal_config_for_prefix` below, so this table only needs one entry
# per journal regardless of how the article id's own prefix is cased.
_JOURNAL_CONFIG_BY_PREFIX: dict[str, dict[str, str]] = {
    "cs": {"display_name": "Clinical Science", "acronym": "CLINSCI"},
    "bcj": {"display_name": "Biochemical Journal", "acronym": "BCJ"},
    "bsr": {"display_name": "Bioscience Reports", "acronym": "BSR"},
    "bst": {"display_name": "Biochemical Society Transactions", "acronym": "BST"},
    "ebc": {"display_name": "Essays in Biochemistry", "acronym": "EBC"},
    "etls": {"display_name": "Emerging Topics in Life Sciences", "acronym": "ETLS"},
}
_ACRONYM_OVERRIDE_BY_ARTICLE_ID = {"cs-2025-8827": "CS"}

# An ENGINE_FAILURE means the engine or its configuration/environment is
# at fault, not the submitted data; everything else is a genuine
# source-data defect. `ArticleTransientError` (S3/DOI-registry/checkpoint-
# store outages, staging/post-write integrity mismatches) is included
# here too: by the time `run_with_retry` has exhausted every retry
# attempt and lets one through, it is by definition an infrastructure
# problem the retries couldn't recover from, never the source data's
# fault — see each subclass's own docstring for why it's marked
# `retryable = True` in the first place.
_ENGINE_DEFECT_EXCEPTION_TYPES = (
    ModelBuildError,
    GeneratorInvariantError,
    XmlSerializationError,
    PackageAssemblyError,
    ArticleTransientError,
)


def _classify_failure(exc: Exception) -> PackageStatus:
    if isinstance(exc, _ENGINE_DEFECT_EXCEPTION_TYPES):
        return PackageStatus.ENGINE_FAILURE
    if isinstance(exc, MecaEngineError):
        return PackageStatus.FATAL_FAILURE
    return PackageStatus.ENGINE_FAILURE


def _journal_prefix(article_id: str) -> str:
    prefix = []
    for ch in article_id:
        if ch.isalpha():
            prefix.append(ch)
        else:
            break
    return "".join(prefix)


def _journal_config_for_prefix(prefix: str) -> dict[str, str]:
    """Look up journal config case-insensitively; ``article_id`` casing is untouched by this."""
    return _JOURNAL_CONFIG_BY_PREFIX[prefix.lower()]


class Worker:
    """Processes one :class:`~meca_engine.service.job.Job` at a time.

    Never knows whether ``input_provider``/``output_provider`` are backed
    by a local directory, S3, or SFTP — it only calls the
    :class:`~meca_engine.providers.input.InputProvider`/
    :class:`~meca_engine.providers.output.OutputProvider` interface.
    """

    def __init__(
        self,
        *,
        input_provider: InputProvider,
        output_provider: OutputProvider,
        output_router: OutputRouter,
        package_batch_runner: PackageBatchRunner,
        runtime_config: RuntimeConfig,
        media_type_config: MediaTypeConfig,
        feature_flags: FeatureFlagsConfig,
        publisher_config: PublisherConfig,
        retry_settings: RetrySettings,
    ) -> None:
        """Initialize the worker with every dependency constructed once per batch."""
        self._input_provider = input_provider
        self._output_provider = output_provider
        self._output_router = output_router
        self._package_batch_runner = package_batch_runner
        self._runtime_config = runtime_config
        self._media_type_config = media_type_config
        self._feature_flags = feature_flags
        self._publisher_config = publisher_config
        self._retry_settings = retry_settings
        self._config_checksum: str | None = None

    def _get_config_checksum(self) -> str:
        """Compute once (lazily, on first real use) and reuse for the rest of the batch.

        `runtime_config`/`feature_flags` never change within a batch (see
        this class's own docstring), so recomputing this SHA-256-over-a-
        deep-dataclass-walk on every single article would be pure repeated
        work at scale. Lazy (not computed in ``__init__``) so a caller that
        never reaches package generation (e.g. a unit test exercising only
        the skip/fail paths, with a stub ``runtime_config``) never pays for
        or needs a real one.
        """
        if self._config_checksum is None:
            self._config_checksum = compute_config_checksum(
                self._runtime_config, self._feature_flags
            )
        return self._config_checksum

    def process(self, job: Job) -> ConversionReport | None:
        """Run one job to completion, retrying transient failures only.

        Args:
            job: The job to process; its lifecycle fields are updated in
                place as processing proceeds.

        Returns:
            The resulting :class:`~meca_engine.packaging.conversion_report.ConversionReport`,
            or ``None`` if the article was already complete from a prior
            run's checkpoint (a "skipped" job — nothing to report this run).
        """
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        logger = get_logger(f"service.{job.article_id}")
        try:
            report = run_with_retry(
                lambda: self._process_once(job, logger),
                settings=self._retry_settings,
                logger=logger,
                on_retry=lambda attempt, exc, delay: setattr(job, "retry_count", attempt),
            )
            job.status = JobStatus.SKIPPED if report is None else JobStatus.SUCCEEDED
            return report
        except MecaEngineError as exc:
            logger.log_exception(exc)
            report = build_conversion_report(
                job.article_id, error=exc, failed_status=_classify_failure(exc)
            )
            job.output_location = str(self._output_router.route_failed_article(report))
            job.status = JobStatus.FAILED
            return report
        except Exception as exc:  # noqa: BLE001
            wrapped = MecaEngineError(
                str(exc), article_id=job.article_id, stage=_STAGE, inner_cause=exc
            )
            logger.log_exception(wrapped)
            report = build_conversion_report(
                job.article_id, error=wrapped, failed_status=PackageStatus.ENGINE_FAILURE
            )
            job.output_location = str(self._output_router.route_failed_article(report))
            job.status = JobStatus.FAILED
            return report
        finally:
            job.finished_at = datetime.now(timezone.utc)

    def _process_once(self, job: Job, logger: StructuredLogger) -> ConversionReport | None:
        article_id = job.article_id
        staged_article = self._input_provider.stage_article(article_id)
        job.input_location = str(staged_article.staged_root)
        try:
            return self._process_staged_article(job, logger, staged_article)
        finally:
            # Never leave an extracted working directory behind, win or
            # lose — matches 13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md
            # §9.4's existing lifecycle; at 6,000-100,000 articles/batch
            # this is the difference between a stable, weeks-long run and
            # one that fills local disk.
            if staged_article.extraction_root is not None:
                shutil.rmtree(staged_article.extraction_root, ignore_errors=True)

    def _process_staged_article(
        self, job: Job, logger: StructuredLogger, staged_article: StagedArticle
    ) -> ConversionReport | None:
        article_id = job.article_id
        xml_path = staged_article.source_xml_path

        document = XmlLoader(logger).load(xml_path)
        bundle = extract_all_metadata(document, logger)

        coordinator = TransformationCoordinator(
            media_type_config=self._media_type_config,
            logger=logger,
            feature_flags=self._feature_flags,
        )
        model = coordinator.build_model(
            article_id=article_id,
            source_object_key=f"{article_id}/{xml_path.name}",
            staged_root=str(staged_article.staged_root),
            parsed_document=document,
            extraction_bundle=bundle,
        )

        prefix = _journal_prefix(article_id)
        journal_defaults = _journal_config_for_prefix(prefix)
        journal_name = journal_defaults["display_name"]
        acronym = _ACRONYM_OVERRIDE_BY_ARTICLE_ID.get(article_id, journal_defaults["acronym"])
        journal_config = JournalConfig(
            journal_id=model.identity.journal_id,
            display_name=journal_name,
            doi_prefix="10.1042",
            acronym=acronym,
            article_type_mapping_ref="article-type-mapping.yaml",
            license_templates_ref="license-templates.yaml",
            doi_registry_scope="per-journal",
            publisher_id="portland-press",
        )
        job.journal = journal_name

        diagnostics = DiagnosticsCollector()
        context = GeneratorContext(
            model=model,
            runtime_config=self._runtime_config,
            journal_config=journal_config,
            publisher_config=self._publisher_config,
            feature_flags=self._feature_flags,
            logger=logger,
            diagnostics=diagnostics,
            source_xml_bytes=document.raw_bytes,
        )

        article_output_root = self._output_provider.article_output_root(article_id)

        outcome = self._package_batch_runner.run([context], output_root=article_output_root)[0]
        if outcome.status is PackageOutcomeStatus.SKIPPED:
            return None
        if outcome.status is PackageOutcomeStatus.FAILED:
            if outcome.exception is not None:
                raise outcome.exception
            raise MecaEngineError(
                outcome.error_message or "package assembly failed",
                article_id=article_id,
                stage=_STAGE,
            )

        assert outcome.staged_package is not None  # noqa: S101 (SUCCEEDED always carries one)
        report = build_conversion_report(
            article_id, staged_package=outcome.staged_package, journal=journal_name
        )
        validation_report = validate_staged_package(outcome.staged_package)
        reproducibility = build_reproducibility_info(
            self._runtime_config, self._feature_flags, config_checksum=self._get_config_checksum()
        )
        report = dataclasses.replace(
            report, validation_report=validation_report, reproducibility=reproducibility
        )
        embed_conversion_report(outcome.staged_package.zip_path, report)
        write_certification_report(
            report, article_output_root / f"MECA_{article_id}_Certification_Report.html"
        )
        write_validation_report(
            validation_report, article_output_root / f"MECA_{article_id}_Validation_Report.html"
        )
        write_migration_audit_report(
            report, article_output_root / f"MECA_{article_id}_Migration_Audit_Report.html"
        )
        write_migration_audit_json(report, article_output_root / "migration-audit.json")
        write_transformation_summary(
            report, article_output_root / f"MECA_{article_id}_Transformation_Summary.html"
        )

        final_location = self._output_router.route_built_package(
            article_id, article_output_root, report
        )
        job.output_location = str(final_location)
        return report
