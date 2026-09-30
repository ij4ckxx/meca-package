"""Unit tests for meca_engine.input.staging.Stager."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from meca_engine.exceptions import InsufficientDiskSpaceError, StagingIntegrityError
from meca_engine.input.discovery import BatchDiscovery
from meca_engine.input.models import LocalBatchSource
from meca_engine.input.readers.base import InputReader
from meca_engine.input.readers.local_reader import LocalFolderReader
from meca_engine.input.staging import Stager
from meca_engine.logging_ import get_logger

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


@pytest.fixture
def discovered_article(valid_batch_root: Path):
    discovery = BatchDiscovery(LocalFolderReader(), get_logger("test.staging.discovery"))
    batch = discovery.discover(LocalBatchSource(root_path=valid_batch_root), batch_id="b1")
    return next(ref for ref in batch.article_refs if ref.article_id == "ART-0001")


def test_stage_article_copies_every_file_with_checksum(discovered_article, tmp_path: Path) -> None:
    working_root = tmp_path / "work"
    stager = Stager(LocalFolderReader(), working_root, get_logger("test.stager"), run_id="run-1")

    staged = stager.stage_article(discovered_article)

    assert staged.article_id == "ART-0001"
    assert staged.working_directory == working_root / "run-1" / "ART-0001"
    assert len(staged.file_inventory.files) == 3
    for record in staged.file_inventory.files:
        assert record.checksum is not None
        assert record.staged_local_path is not None
        assert record.staged_local_path.is_file()
        assert record.staged_local_path.read_bytes()


def test_stage_article_preserves_round_subfolder_layout(discovered_article, tmp_path: Path) -> None:
    working_root = tmp_path / "work"
    stager = Stager(LocalFolderReader(), working_root, get_logger("test.stager"), run_id="run-1")

    staged = stager.stage_article(discovered_article)

    manuscript = next(
        r
        for r in staged.file_inventory.files
        if r.round_label == "R1" and r.relative_path == "manuscript.txt"
    )
    assert (
        manuscript.staged_local_path
        == working_root / "run-1" / "ART-0001" / "R1" / "manuscript.txt"
    )


def test_working_directory_is_created(discovered_article, tmp_path: Path) -> None:
    working_root = tmp_path / "work"
    stager = Stager(LocalFolderReader(), working_root, get_logger("test.stager"), run_id="run-1")

    assert not working_root.exists()
    stager.stage_article(discovered_article)
    assert (working_root / "run-1" / "ART-0001").is_dir()


def test_cleanup_removes_the_working_directory(discovered_article, tmp_path: Path) -> None:
    working_root = tmp_path / "work"
    stager = Stager(LocalFolderReader(), working_root, get_logger("test.stager"), run_id="run-1")
    staged = stager.stage_article(discovered_article)
    assert staged.working_directory.exists()

    stager.cleanup(staged.working_directory)

    assert not staged.working_directory.exists()


def test_cleanup_never_raises_for_an_already_missing_directory(tmp_path: Path) -> None:
    stager = Stager(LocalFolderReader(), tmp_path / "work", get_logger("test.stager"))

    stager.cleanup(tmp_path / "work" / "never-existed")  # must not raise


def test_disk_space_failure_raises_and_cleans_up(
    discovered_article, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    working_root = tmp_path / "work"
    stager = Stager(LocalFolderReader(), working_root, get_logger("test.stager"), run_id="run-1")

    class _FakeUsage:
        free = 0

    monkeypatch.setattr(shutil, "disk_usage", lambda _path: _FakeUsage())

    with pytest.raises(InsufficientDiskSpaceError):
        stager.stage_article(discovered_article)

    assert not (working_root / "run-1" / "ART-0001").exists()


def _make_size_mismatch_reader(delegate: InputReader) -> InputReader:
    class _SizeMismatchReader(InputReader):
        def list_batch_article_ids(self, source):  # type: ignore[no-untyped-def]
            return delegate.list_batch_article_ids(source)

        def list_article_top_level(self, article_id, source):  # type: ignore[no-untyped-def]
            return delegate.list_article_top_level(article_id, source)

        def list_round_files(self, article_id, round_label, source):  # type: ignore[no-untyped-def]
            return delegate.list_round_files(article_id, round_label, source)

        def fetch_file(self, article_id, round_label, relative_path, source, destination):  # type: ignore[no-untyped-def]
            destination.write_bytes(b"short")
            return "irrelevant-checksum", 5

    return _SizeMismatchReader()


def test_size_mismatch_raises_staging_integrity_error_and_cleans_up(
    discovered_article, tmp_path: Path
) -> None:
    working_root = tmp_path / "work"
    mismatched_reader = _make_size_mismatch_reader(LocalFolderReader())
    stager = Stager(mismatched_reader, working_root, get_logger("test.stager"), run_id="run-1")

    with pytest.raises(StagingIntegrityError, match="Size mismatch"):
        stager.stage_article(discovered_article)

    assert not (working_root / "run-1" / "ART-0001").exists()


def _make_wrong_checksum_reader(delegate: InputReader) -> InputReader:
    class _WrongChecksumReader(InputReader):
        def list_batch_article_ids(self, source):  # type: ignore[no-untyped-def]
            return delegate.list_batch_article_ids(source)

        def list_article_top_level(self, article_id, source):  # type: ignore[no-untyped-def]
            return delegate.list_article_top_level(article_id, source)

        def list_round_files(self, article_id, round_label, source):  # type: ignore[no-untyped-def]
            return delegate.list_round_files(article_id, round_label, source)

        def fetch_file(self, article_id, round_label, relative_path, source, destination):  # type: ignore[no-untyped-def]
            _real_checksum, size = delegate.fetch_file(
                article_id, round_label, relative_path, source, destination
            )
            return "0" * 64, size  # correct bytes on disk, wrong claimed checksum

    return _WrongChecksumReader()


def test_checksum_mismatch_raises_staging_integrity_error_and_cleans_up(
    discovered_article, tmp_path: Path
) -> None:
    working_root = tmp_path / "work"
    wrong_checksum_reader = _make_wrong_checksum_reader(LocalFolderReader())
    stager = Stager(wrong_checksum_reader, working_root, get_logger("test.stager"), run_id="run-1")

    with pytest.raises(StagingIntegrityError, match="Checksum mismatch"):
        stager.stage_article(discovered_article)

    assert not (working_root / "run-1" / "ART-0001").exists()


def test_run_id_auto_generated_when_not_supplied(tmp_path: Path) -> None:
    stager = Stager(LocalFolderReader(), tmp_path / "work", get_logger("test.stager"))

    assert stager.run_id  # non-empty, auto-generated
