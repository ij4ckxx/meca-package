"""Unit tests for meca_engine.service.processing_service.ProcessingService.

Scoped to the new orchestration wiring this phase adds — article id
filtering, and control-file-driven cancel/stop-after-current — using
fakes for InputProvider/Worker so no real conversion pipeline is needed.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from meca_engine.packaging.conversion_report import ConversionReport
from meca_engine.packaging.models import PackageStatus
from meca_engine.service.control import ControlCommand, write_command
from meca_engine.service.processing_service import ProcessingService

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.service.job import Job

pytestmark = pytest.mark.unit


class _FakeInputProvider:
    def __init__(self, article_ids: tuple[str, ...]) -> None:
        self._article_ids = article_ids

    def list_articles(self) -> tuple[str, ...]:
        return self._article_ids


class _FakeWorker:
    def __init__(self, *, on_process: object = None) -> None:
        self.processed: list[str] = []
        self._on_process = on_process

    def process(self, job: Job) -> ConversionReport | None:
        self.processed.append(job.article_id)
        if self._on_process is not None:
            self._on_process(job.article_id)  # type: ignore[operator]
        return ConversionReport(
            article_id=job.article_id, status=PackageStatus.CERTIFIED, confidence_score=100
        )


def test_run_processes_every_article(tmp_path: Path) -> None:
    worker = _FakeWorker()
    service = ProcessingService(
        input_provider=_FakeInputProvider(("a-1", "a-2", "a-3")),
        worker=worker,
        reports_dir=tmp_path,
    )

    service.run()

    assert worker.processed == ["a-1", "a-2", "a-3"]
    assert (tmp_path / "conversion_reports.json").is_file()


def test_conversion_reports_json_refreshes_mid_run_not_only_at_the_end(tmp_path: Path) -> None:
    """Regression: the Dashboard's main data source must not sit empty for a whole long run."""
    from meca_engine.service.processing_service import _INCREMENTAL_SNAPSHOT_INTERVAL

    article_ids = tuple(f"a-{i}" for i in range(_INCREMENTAL_SNAPSHOT_INTERVAL + 5))
    report_path = tmp_path / "conversion_reports.json"
    seen_mid_run_snapshot = False

    def check_snapshot_after_threshold(article_id: str) -> None:
        nonlocal seen_mid_run_snapshot
        if article_id == f"a-{_INCREMENTAL_SNAPSHOT_INTERVAL}" and report_path.is_file():
            records = json.loads(report_path.read_text())
            seen_mid_run_snapshot = len(records) == _INCREMENTAL_SNAPSHOT_INTERVAL

    worker = _FakeWorker(on_process=check_snapshot_after_threshold)
    service = ProcessingService(
        input_provider=_FakeInputProvider(article_ids), worker=worker, reports_dir=tmp_path
    )

    service.run()

    assert seen_mid_run_snapshot
    assert len(json.loads(report_path.read_text())) == len(article_ids)


def test_one_articles_worker_exception_never_stops_the_batch(tmp_path: Path) -> None:
    """Regression: even a bug in the Worker's own error handling must not abort the batch."""

    class _FlakyWorker:
        def process(self, job: Job) -> ConversionReport | None:
            if job.article_id == "a-2":
                raise RuntimeError("simulated failure inside the worker's own error handling")
            return ConversionReport(
                article_id=job.article_id, status=PackageStatus.CERTIFIED, confidence_score=100
            )

    service = ProcessingService(
        input_provider=_FakeInputProvider(("a-1", "a-2", "a-3")),
        worker=_FlakyWorker(),
        reports_dir=tmp_path,
    )

    snapshot = service.run()

    processed_ids = [p.article_id for p in snapshot.packages]
    assert processed_ids == ["a-1", "a-2", "a-3"]
    records = json.loads((tmp_path / "conversion_reports.json").read_text())
    by_id = {r["article_id"]: r for r in records}
    assert by_id["a-2"]["status"] == "engine_failure"
    assert by_id["a-1"]["status"] == "certified"
    assert by_id["a-3"]["status"] == "certified"


def test_restarting_a_subset_preserves_prior_articles_in_conversion_reports(
    tmp_path: Path,
) -> None:
    """Regression: reusing a batch-id for a narrower restart must not drop prior records."""
    ProcessingService(
        input_provider=_FakeInputProvider(("a-1", "a-2", "a-3")),
        worker=_FakeWorker(),
        reports_dir=tmp_path,
    ).run()

    ProcessingService(
        input_provider=_FakeInputProvider(("a-1", "a-2", "a-3")),
        worker=_FakeWorker(),
        reports_dir=tmp_path,
        article_id_filter=frozenset({"a-2"}),
    ).run()

    records = json.loads((tmp_path / "conversion_reports.json").read_text())
    assert {r["article_id"] for r in records} == {"a-1", "a-2", "a-3"}


def test_article_id_filter_restricts_processing(tmp_path: Path) -> None:
    worker = _FakeWorker()
    service = ProcessingService(
        input_provider=_FakeInputProvider(("a-1", "a-2", "a-3")),
        worker=worker,
        reports_dir=tmp_path,
        article_id_filter=frozenset({"a-2"}),
    )

    service.run()

    assert worker.processed == ["a-2"]


def test_cancel_stops_before_any_article_is_processed(tmp_path: Path) -> None:
    control_path = tmp_path / "control.json"
    write_command(control_path, ControlCommand.CANCEL)
    worker = _FakeWorker()
    service = ProcessingService(
        input_provider=_FakeInputProvider(("a-1", "a-2")),
        worker=worker,
        reports_dir=tmp_path,
        control_path=control_path,
        status_path=tmp_path / "live_status.json",
    )

    service.run()

    assert worker.processed == []
    status = json.loads((tmp_path / "live_status.json").read_text())
    assert status["state"] == "cancelled"


def test_stop_after_current_processes_one_more_article_then_stops(tmp_path: Path) -> None:
    control_path = tmp_path / "control.json"
    status_path = tmp_path / "live_status.json"

    def request_stop_mid_first_article(_article_id: str) -> None:
        write_command(control_path, ControlCommand.STOP_AFTER_CURRENT)

    worker = _FakeWorker(on_process=request_stop_mid_first_article)
    service = ProcessingService(
        input_provider=_FakeInputProvider(("a-1", "a-2", "a-3")),
        worker=worker,
        reports_dir=tmp_path,
        control_path=control_path,
        status_path=status_path,
    )

    service.run()

    assert worker.processed == ["a-1"]
    status = json.loads(status_path.read_text())
    assert status["state"] == "stopped"
    assert status["completed"] == 1
