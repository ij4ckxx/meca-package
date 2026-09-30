"""Unit tests for meca_engine.orchestrator.run_controller.RunController."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from meca_engine.checkpoint.backends.in_memory import InMemoryCheckpointStore
from meca_engine.checkpoint.models import ArticleStage
from meca_engine.exceptions import InsufficientDiskSpaceError
from meca_engine.input.discovery import BatchDiscovery
from meca_engine.input.models import LocalBatchSource
from meca_engine.input.readers.base import InputReader
from meca_engine.input.readers.local_reader import LocalFolderReader
from meca_engine.input.staging import Stager
from meca_engine.logging_ import get_logger
from meca_engine.orchestrator.models import OutcomeStatus
from meca_engine.orchestrator.run_controller import RunController
from meca_engine.orchestrator.scheduler import SequentialWorkerScheduler

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def _build_controller(
    root: Path, working_root: Path, checkpoint_store: InMemoryCheckpointStore, *, reader=None
) -> RunController:
    reader = reader or LocalFolderReader()
    discovery = BatchDiscovery(reader, get_logger("test.run_controller.discovery"))
    stager = Stager(reader, working_root, get_logger("test.run_controller.stager"), run_id="run-1")
    scheduler = SequentialWorkerScheduler()
    return RunController(
        discovery,
        stager,
        checkpoint_store,
        scheduler,
        get_logger("test.run_controller"),
        run_id="run-1",
    )


def test_full_batch_succeeds(valid_batch_root: Path, tmp_path: Path) -> None:
    controller = _build_controller(valid_batch_root, tmp_path / "work", InMemoryCheckpointStore())

    summary = controller.run(LocalBatchSource(root_path=valid_batch_root), batch_id="b1")

    assert summary.succeeded_count == 2
    assert summary.failed_count == 0
    assert summary.skipped_count == 0
    assert summary.total_discovered == 2
    assert summary.total_discovery_failures == 0
    for outcome in summary.outcomes:
        assert outcome.status is OutcomeStatus.SUCCESS
        assert outcome.staged_article is not None


def test_checkpoint_reflects_staged_state_after_success(
    valid_batch_root: Path, tmp_path: Path
) -> None:
    checkpoint_store = InMemoryCheckpointStore()
    controller = _build_controller(valid_batch_root, tmp_path / "work", checkpoint_store)

    controller.run(LocalBatchSource(root_path=valid_batch_root), batch_id="b1")

    record = checkpoint_store.get_record("ART-0001")
    assert record is not None
    assert record.stage is ArticleStage.STAGED


def test_resume_skips_already_staged_articles(valid_batch_root: Path, tmp_path: Path) -> None:
    checkpoint_store = InMemoryCheckpointStore()
    source = LocalBatchSource(root_path=valid_batch_root)

    first_controller = _build_controller(valid_batch_root, tmp_path / "work", checkpoint_store)
    first_summary = first_controller.run(source, batch_id="b1")
    assert first_summary.succeeded_count == 2

    stage_calls: list[str] = []
    real_reader = LocalFolderReader()

    class _CountingReader(InputReader):
        def list_batch_article_ids(self, source):  # type: ignore[no-untyped-def]
            return real_reader.list_batch_article_ids(source)

        def list_article_top_level(self, article_id, source):  # type: ignore[no-untyped-def]
            return real_reader.list_article_top_level(article_id, source)

        def list_round_files(self, article_id, round_label, source):  # type: ignore[no-untyped-def]
            return real_reader.list_round_files(article_id, round_label, source)

        def fetch_file(self, article_id, round_label, relative_path, source, destination):  # type: ignore[no-untyped-def]
            stage_calls.append(article_id)
            return real_reader.fetch_file(
                article_id, round_label, relative_path, source, destination
            )

    second_controller = _build_controller(
        valid_batch_root, tmp_path / "work2", checkpoint_store, reader=_CountingReader()
    )
    second_summary = second_controller.run(source, batch_id="b1")

    assert second_summary.skipped_count == 2
    assert second_summary.succeeded_count == 0
    assert stage_calls == []  # no file was re-fetched; nothing was re-staged


def test_discovery_failure_recorded_without_blocking_other_articles(
    valid_batch_root: Path, tmp_path: Path
) -> None:
    # Add a third, structurally-invalid article alongside the 2 valid ones.
    bad_dir = valid_batch_root / "ART-BAD"
    bad_dir.mkdir()

    controller = _build_controller(valid_batch_root, tmp_path / "work", InMemoryCheckpointStore())
    summary = controller.run(LocalBatchSource(root_path=valid_batch_root), batch_id="b1")

    assert summary.succeeded_count == 2
    assert summary.total_discovery_failures == 1
    failed_outcomes = [o for o in summary.outcomes if o.status is OutcomeStatus.FAILED]
    assert len(failed_outcomes) == 1
    assert failed_outcomes[0].article_id == "ART-BAD"
    assert failed_outcomes[0].exception_type == "InvalidArticlePackageError"


def test_staging_failure_isolated_to_one_article(valid_batch_root: Path, tmp_path: Path) -> None:
    real_reader = LocalFolderReader()

    class _FailOneArticleReader(InputReader):
        def list_batch_article_ids(self, source):  # type: ignore[no-untyped-def]
            return real_reader.list_batch_article_ids(source)

        def list_article_top_level(self, article_id, source):  # type: ignore[no-untyped-def]
            return real_reader.list_article_top_level(article_id, source)

        def list_round_files(self, article_id, round_label, source):  # type: ignore[no-untyped-def]
            return real_reader.list_round_files(article_id, round_label, source)

        def fetch_file(self, article_id, round_label, relative_path, source, destination):  # type: ignore[no-untyped-def]
            if article_id == "ART-0001":
                destination.write_bytes(b"wrong-length")
                return "irrelevant", 999999  # size mismatch -> StagingIntegrityError
            return real_reader.fetch_file(
                article_id, round_label, relative_path, source, destination
            )

    checkpoint_store = InMemoryCheckpointStore()
    controller = _build_controller(
        valid_batch_root, tmp_path / "work", checkpoint_store, reader=_FailOneArticleReader()
    )

    summary = controller.run(LocalBatchSource(root_path=valid_batch_root), batch_id="b1")

    assert summary.succeeded_count == 1
    assert summary.failed_count == 1
    failed = next(o for o in summary.outcomes if o.status is OutcomeStatus.FAILED)
    assert failed.article_id == "ART-0001"
    assert failed.exception_type == "StagingIntegrityError"
    assert checkpoint_store.get_record("ART-0001").stage is ArticleStage.FAILED  # type: ignore[union-attr]
    assert checkpoint_store.get_record("ART-0002").stage is ArticleStage.STAGED  # type: ignore[union-attr]


def test_failed_article_is_retried_not_skipped_on_next_run(
    valid_batch_root: Path, tmp_path: Path
) -> None:
    checkpoint_store = InMemoryCheckpointStore()
    checkpoint_store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGING)
    checkpoint_store.transition(
        "ART-0001",
        expected_current=ArticleStage.STAGING,
        new_stage=ArticleStage.FAILED,
        failure_reason="previous attempt failed",
    )

    controller = _build_controller(valid_batch_root, tmp_path / "work", checkpoint_store)
    summary = controller.run(LocalBatchSource(root_path=valid_batch_root), batch_id="b1")

    art1_outcome = next(o for o in summary.outcomes if o.article_id == "ART-0001")
    assert art1_outcome.status is OutcomeStatus.SUCCESS
    assert checkpoint_store.get_record("ART-0001").stage is ArticleStage.STAGED  # type: ignore[union-attr]


def test_checkpoint_transition_collision_yields_skipped_outcome(
    valid_batch_root: Path, tmp_path: Path
) -> None:
    """Simulate a race: another worker claims the article between our read and write."""

    class _RacyCheckpointStore(InMemoryCheckpointStore):
        def get_record(self, article_id: str):  # type: ignore[no-untyped-def]
            return None  # always reports "not started", even if actually claimed

    checkpoint_store = _RacyCheckpointStore()
    # Simulate a concurrent worker having already claimed this article.
    checkpoint_store.transition("ART-0001", expected_current=None, new_stage=ArticleStage.STAGING)

    controller = _build_controller(valid_batch_root, tmp_path / "work", checkpoint_store)
    summary = controller.run(LocalBatchSource(root_path=valid_batch_root), batch_id="b1")

    art1_outcome = next(o for o in summary.outcomes if o.article_id == "ART-0001")
    assert art1_outcome.status is OutcomeStatus.SKIPPED
    assert art1_outcome.error_message == "checkpoint transition collision"


def test_batch_level_error_propagates_and_halts_the_run(
    valid_batch_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = _build_controller(valid_batch_root, tmp_path / "work", InMemoryCheckpointStore())

    class _FakeUsage:
        free = 0

    monkeypatch.setattr(shutil, "disk_usage", lambda _path: _FakeUsage())

    with pytest.raises(InsufficientDiskSpaceError):
        controller.run(LocalBatchSource(root_path=valid_batch_root), batch_id="b1")
