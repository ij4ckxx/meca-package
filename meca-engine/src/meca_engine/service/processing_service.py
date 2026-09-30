"""Processing Service — the single orchestration entry point.

Loads packages via the configured :class:`~meca_engine.providers.input.InputProvider`,
creates one :class:`~meca_engine.service.job.Job` per article, drains them
sequentially through a :class:`~meca_engine.service.worker.Worker`, and
produces the same corpus-level reports/intelligence artifacts the batch
script always has — unchanged, just relocated here so the script itself
becomes a thin bootstrap.
"""

from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING

from meca_engine.exceptions import MecaEngineError
from meca_engine.logging_ import get_logger
from meca_engine.packaging.conversion_report import build_conversion_report
from meca_engine.packaging.models import PackageStatus
from meca_engine.reporting.analytics import (
    write_business_rule_statistics,
    write_recovery_analytics,
)
from meca_engine.reporting.batch_audit_report import write_batch_audit_report
from meca_engine.reporting.csv_reports import write_archive_audit_csv, write_manual_review_csv
from meca_engine.reporting.dashboard import write_dashboard_json
from meca_engine.reporting.migration_summary import write_migration_summary
from meca_engine.reporting.operator_checklist import write_operator_checklist
from meca_engine.service.control import (
    ControlCommand,
    LiveStatusWriter,
    RunState,
    wait_while_paused,
)
from meca_engine.service.job import Job, JobStatus
from meca_engine.service.progress import ProgressTracker
from meca_engine.service.queue import JobQueue
from meca_engine.service.status import BatchStatusSnapshot, build_status_view

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.packaging.conversion_report import ConversionReport
    from meca_engine.providers.input import InputProvider
    from meca_engine.service.status import PackageStatusView
    from meca_engine.service.worker import Worker

# How often (in completed articles) `conversion_reports.json` — the
# Dashboard's primary per-article data source — is refreshed mid-run.
# Every article would make the Dashboard maximally fresh but costs O(n^2)
# total I/O across a large batch (rewriting an ever-larger file each
# time); this bounds that cost while keeping a long run's Dashboard view
# from sitting empty/stale for its whole duration.
_INCREMENTAL_SNAPSHOT_INTERVAL = 25

_GENERATED_STATUSES = (
    PackageStatus.CERTIFIED,
    PackageStatus.CERTIFIED_WITH_WARNINGS,
    PackageStatus.CERTIFIED_WITH_RECOVERY,
    PackageStatus.PARTIAL_CERTIFICATION,
)


class ProcessingService:
    """Orchestrates one full batch run, sequentially, through a single :class:`Worker`."""

    def __init__(
        self,
        *,
        input_provider: InputProvider,
        worker: Worker,
        reports_dir: Path,
        article_id_filter: frozenset[str] | None = None,
        control_path: Path | None = None,
        status_path: Path | None = None,
    ) -> None:
        """Initialize the service with its already-wired dependencies.

        Args:
            input_provider: Where articles are discovered/staged from.
            worker: Processes one job at a time.
            reports_dir: Where corpus-level reports are written.
            article_id_filter: If given, only these article ids are
                processed (used for "restart failed/manual-review
                articles only"); ``None`` processes everything the
                provider reports, as before this option existed.
            control_path: If given, checked between articles for a
                pause/stop/cancel command (see :mod:`meca_engine.service.control`).
                ``None`` disables live control entirely.
            status_path: If given, a live-status JSON snapshot is written
                after each article. ``None`` disables it entirely.
        """
        self._input_provider = input_provider
        self._worker = worker
        self._reports_dir = reports_dir
        self._article_id_filter = article_id_filter
        self._control_path = control_path
        self._status_path = status_path

    def run(self) -> BatchStatusSnapshot:
        """Run every job the configured InputProvider reports, and return a status snapshot."""
        article_ids = self._input_provider.list_articles()
        if self._article_id_filter is not None:
            article_ids = tuple(a for a in article_ids if a in self._article_id_filter)
        print(f"Found {len(article_ids)} packages via {type(self._input_provider).__name__}")

        queue = JobQueue()
        for article_id in article_ids:
            queue.enqueue(Job(article_id=article_id))

        progress = ProgressTracker(total=queue.size())
        status_writer = (
            LiveStatusWriter(status_path=self._status_path, total=queue.size())
            if self._status_path is not None
            else None
        )
        reports: list[ConversionReport] = []
        status_views: list[PackageStatusView] = []
        final_state = RunState.COMPLETED
        # Loaded once, not re-read from disk on every snapshot: this run's
        # own `reports` already holds everything it processes in memory,
        # so only a prior run's (restart-subset) records need to come
        # from disk at all.
        prior_reports_by_id = self._load_existing_report_dicts()

        while not queue.empty():
            requested_stop = self._check_control()
            if requested_stop is not None:
                final_state = requested_stop
                break

            job = queue.dequeue()
            assert job is not None  # queue.empty() just confirmed a job exists
            report = self._run_one_job(job, progress, status_writer)
            if report is not None:
                reports.append(report)
                if len(reports) % _INCREMENTAL_SNAPSHOT_INTERVAL == 0:
                    self._write_conversion_reports_json(reports, prior_reports_by_id)
            status_views.append(build_status_view(job, report))

        if status_writer is not None:
            status_writer.finish(final_state)
        progress.finish()
        self._write_reports(reports, prior_reports_by_id)
        self._print_summary(reports)

        return BatchStatusSnapshot(progress=progress.snapshot(), packages=tuple(status_views))

    def _check_control(self) -> RunState | None:
        """Return a terminal state if a stop/cancel was requested, else ``None`` to continue."""
        if self._control_path is None:
            return None
        command = wait_while_paused(self._control_path)
        if command is ControlCommand.CANCEL:
            return RunState.CANCELLED
        if command is ControlCommand.STOP_AFTER_CURRENT:
            return RunState.STOPPED
        return None

    def _run_one_job(
        self, job: Job, progress: ProgressTracker, status_writer: LiveStatusWriter | None
    ) -> ConversionReport | None:
        progress.start_job(job.article_id)
        if status_writer is not None:
            status_writer.start_article(job.article_id)

        t_start = time.perf_counter()
        report = self._process_job_never_raising(job)
        elapsed = round(time.perf_counter() - t_start, 3)

        if report is not None:
            print(f"{job.article_id}: {report.status.value} ({elapsed}s)", flush=True)
        else:
            print(f"{job.article_id}: skipped, already complete ({elapsed}s)", flush=True)

        progress.complete_job()
        if status_writer is not None:
            status_writer.complete_article()
        return report

    def _process_job_never_raising(self, job: Job) -> ConversionReport | None:
        """Last-resort safety net: one article must never be able to end the whole batch.

        `Worker.process()` already classifies and reports every failure it
        knows about — this only exists to catch something even *that*
        didn't anticipate (e.g. its own failure-report write hitting a
        full disk). Reaching this branch is itself a genuine engine
        defect (the engine's own error handling broke), so it is reported
        as `ENGINE_FAILURE`; it deliberately does not attempt any further
        file writes for this article, since the underlying cause may be
        exactly "cannot write files right now."
        """
        try:
            return self._worker.process(job)
        except Exception as exc:  # noqa: BLE001
            get_logger(f"service.{job.article_id}").critical(
                "Article processing raised past the worker's own error handling; "
                "this is an engine defect in error handling itself, not this "
                "article's source data. Continuing with the rest of the batch.",
                stage="meca_engine.service.processing_service",
                context={"article_id": job.article_id, "exception": repr(exc)},
            )
            job.status = JobStatus.FAILED
            return build_conversion_report(
                job.article_id,
                error=MecaEngineError(
                    str(exc),
                    article_id=job.article_id,
                    stage="meca_engine.service.processing_service",
                    inner_cause=exc,
                ),
                failed_status=PackageStatus.ENGINE_FAILURE,
            )

    def _write_conversion_reports_json(
        self, reports: list[ConversionReport], prior_reports_by_id: dict[str, object]
    ) -> None:
        """Atomically (write-then-rename) refresh the Dashboard's per-article data source.

        Called both mid-run (throttled, see `_INCREMENTAL_SNAPSHOT_INTERVAL`)
        and once more at the end with the complete list. Write-then-rename
        (the same pattern `packaging/builder.py` uses for a finished ZIP)
        means a concurrent reader (the Dashboard) never observes a
        partially-written file, mid-run or not.

        Merges with ``prior_reports_by_id`` (loaded once, at the start of
        `run()`, not re-read from disk on every call — this run's own
        `reports` already covers everything processed this run in memory)
        rather than overwriting the file outright — reusing the same
        ``--batch-id`` with a narrower ``--article-ids`` subset (a
        "restart just the failed/manual-review articles" run) must not
        make the Dashboard silently forget every article a prior run
        already completed. A reprocessed article's record is replaced
        with this run's fresher result; every other prior record is kept
        untouched.
        """
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = self._reports_dir / "conversion_reports.json"
        merged: dict[str, object] = dict(prior_reports_by_id)
        for report in reports:
            merged[report.article_id] = report.to_dict()

        tmp_path = report_path.with_suffix(".json.tmp")
        with open(tmp_path, "w") as fh:
            json.dump(list(merged.values()), fh, indent=2, default=str)
        os.replace(tmp_path, report_path)

    def _load_existing_report_dicts(self) -> dict[str, object]:
        report_path = self._reports_dir / "conversion_reports.json"
        if not report_path.is_file():
            return {}
        return {record["article_id"]: record for record in json.loads(report_path.read_text())}

    def _write_reports(
        self, reports: list[ConversionReport], prior_reports_by_id: dict[str, object]
    ) -> None:
        self._write_conversion_reports_json(reports, prior_reports_by_id)

        write_migration_summary(reports, self._reports_dir / "Migration_Summary.html")
        write_archive_audit_csv(reports, self._reports_dir / "Archive_Audit.csv")
        write_manual_review_csv(reports, self._reports_dir / "Manual_Review.csv")
        write_recovery_analytics(reports, self._reports_dir / "Recovery_Analytics.md")
        write_business_rule_statistics(reports, self._reports_dir / "Business_Rule_Statistics.md")
        write_dashboard_json(reports, self._reports_dir / "migration_dashboard.json")

        _write_intelligence_reports(reports, self._reports_dir)

    def _print_summary(self, reports: list[ConversionReport]) -> None:
        total = len(reports)
        counts = {status: 0 for status in PackageStatus}
        for report in reports:
            counts[report.status] += 1

        print("\n=== SUMMARY ===")
        print(f"Total: {total}")
        for status in PackageStatus:
            print(f"  {status.value}: {counts[status]}")

        generated = sum(1 for r in reports if r.status in _GENERATED_STATUSES)
        total_warnings = sum(len(r.warnings) for r in reports)
        total_recoveries = sum(len(r.recoveries) for r in reports)

        print(f"\nPackages generated: {generated}/{total}")
        print(f"Total warnings: {total_warnings}")
        print(f"Total recoveries: {total_recoveries}")
        print(f"Engine failures: {counts[PackageStatus.ENGINE_FAILURE]}")
        print(f"Fatal failures: {counts[PackageStatus.FATAL_FAILURE]}")


def _write_intelligence_reports(reports: list[ConversionReport], reports_dir: Path) -> None:
    """Milestone 14: analytics-only reports, built entirely from ``reports`` already in hand."""
    from meca_engine.reporting.intelligence import business_rule_statistics as intel_br
    from meca_engine.reporting.intelligence import confidence_statistics as intel_confidence
    from meca_engine.reporting.intelligence import (
        corpus_analyzer,
        recommendation_engine,
        trend_analyzer,
    )
    from meca_engine.reporting.intelligence import journal_statistics as intel_journal
    from meca_engine.reporting.intelligence import recovery_statistics as intel_rr
    from meca_engine.reporting.intelligence import warning_statistics as intel_warn

    records = corpus_analyzer.build_corpus(reports)

    corpus_analyzer.write_migration_intelligence_report(
        reports, reports_dir / "Migration_Intelligence_Report.html"
    )
    intel_journal.write_journal_health_report(records, reports_dir / "Journal_Health_Report.html")
    intel_br.write_business_rule_effectiveness(
        records, reports_dir / "Business_Rule_Effectiveness.md"
    )
    intel_rr.write_recovery_rule_effectiveness(
        records, reports_dir / "Recovery_Rule_Effectiveness.md"
    )
    intel_warn.write_warning_frequency(records, reports_dir / "Warning_Frequency.md")
    intel_confidence.write_confidence_analysis(records, reports_dir / "Confidence_Analysis.md")

    journal_stats = intel_journal.compute_journal_statistics(records)
    br_stats = intel_br.compute_business_rule_statistics(records)
    rr_stats = intel_rr.compute_recovery_rule_statistics(records)
    warn_stats = intel_warn.compute_warning_statistics(records)
    recommendations = recommendation_engine.generate_recommendations(
        records, journal_stats, br_stats, rr_stats, warn_stats
    )
    recommendation_engine.write_recommendations(recommendations, reports_dir / "Recommendations.md")

    trends = trend_analyzer.build_trends_json(
        [trend_analyzer.BatchSnapshot(label="current", records=records)]
    )
    (reports_dir / "Migration_Trends.json").write_text(json.dumps(trends, indent=2))

    dashboard = corpus_analyzer.build_dashboard_intelligence(reports)
    (reports_dir / "dashboard_intelligence.json").write_text(json.dumps(dashboard, indent=2))

    confidence_stats = intel_confidence.compute_confidence_statistics(records)
    write_batch_audit_report(
        reports,
        records,
        journal_stats,
        br_stats,
        rr_stats,
        confidence_stats,
        reports_dir / "Batch_Audit_Report.html",
    )
    write_operator_checklist(reports, reports_dir / "Operator_Checklist.html")
