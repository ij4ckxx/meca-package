"""Dashboard-ready status views, built entirely from existing report/job data.

No new computation: every field here is read straight off an already-built
:class:`~meca_engine.packaging.conversion_report.ConversionReport` (Milestone
12's reporting/certification/confidence/recovery calculations) or a
:class:`~meca_engine.service.job.Job`. A future dashboard consumes
:class:`PackageStatusView`/:class:`BatchStatusSnapshot` directly; the engine
never changes to support it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meca_engine.model.warnings import ConfidenceLevel, EngineWarning
    from meca_engine.packaging.conversion_report import ConversionReport
    from meca_engine.packaging.models import PackageStatus
    from meca_engine.service.job import Job, JobStatus
    from meca_engine.service.progress import ProgressSnapshot


@dataclass(frozen=True)
class PackageStatusView:
    """One article's dashboard-facing status, combining its Job and ConversionReport.

    Attributes:
        job_id: The job that processed this article.
        article_id: The article this view describes.
        journal: The article's journal display name.
        job_status: The job's own lifecycle status.
        conversion_status: The certification outcome, or ``None`` if no
            report was produced this run (a job skipped because it was
            already complete from a prior run's checkpoint).
        confidence_score: 0-100 advisory signal, or ``None`` if skipped.
        overall_confidence: Bucketed confidence, or ``None`` if skipped.
        warnings: Advisory findings for this article.
        recoveries: Recovery Rule applications for this article.
        business_rules_failed: Tracked Business Rules with a finding
            against this article.
        generated_files: Every physical file packaged.
        download_location: Where the finished package was written, if any.
        retry_count: How many transient-failure retries this job needed.
        duration_seconds: Total processing time for this job.
    """

    job_id: str
    article_id: str
    journal: str
    job_status: JobStatus
    conversion_status: PackageStatus | None
    confidence_score: int | None
    overall_confidence: ConfidenceLevel | None
    warnings: tuple[EngineWarning, ...]
    recoveries: tuple[EngineWarning, ...]
    business_rules_failed: tuple[str, ...]
    generated_files: tuple[str, ...]
    download_location: str | None
    retry_count: int
    duration_seconds: float | None


def build_status_view(job: Job, report: ConversionReport | None) -> PackageStatusView:
    """Build a :class:`PackageStatusView` from a finished job and its report.

    Args:
        job: The job, after :meth:`~meca_engine.service.worker.Worker.process`
            has updated its lifecycle fields.
        report: The report produced this run, or ``None`` if the job was
            skipped as already complete.
    """
    return PackageStatusView(
        job_id=job.job_id,
        article_id=job.article_id,
        journal=job.journal,
        job_status=job.status,
        conversion_status=report.status if report is not None else None,
        confidence_score=report.confidence_score if report is not None else None,
        overall_confidence=report.overall_confidence if report is not None else None,
        warnings=report.warnings if report is not None else (),
        recoveries=report.recoveries if report is not None else (),
        business_rules_failed=report.business_rules_failed if report is not None else (),
        generated_files=report.generated_files if report is not None else (),
        download_location=job.output_location or None,
        retry_count=job.retry_count,
        duration_seconds=job.duration_seconds,
    )


@dataclass(frozen=True)
class BatchStatusSnapshot:
    """Everything a future dashboard needs for one batch run, in one object."""

    progress: ProgressSnapshot
    packages: tuple[PackageStatusView, ...]
