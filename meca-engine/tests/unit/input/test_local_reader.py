"""Unit tests for meca_engine.input.readers.local_reader.LocalFolderReader."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from meca_engine.exceptions import SourceUnavailableError
from meca_engine.input.models import LocalBatchSource, S3BatchSource
from meca_engine.input.readers.local_reader import LocalFolderReader

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


@pytest.fixture
def reader() -> LocalFolderReader:
    return LocalFolderReader()


def test_list_batch_article_ids_returns_sorted_directory_names(
    reader: LocalFolderReader, valid_batch_root: Path
) -> None:
    ids = reader.list_batch_article_ids(LocalBatchSource(root_path=valid_batch_root))

    assert ids == ("ART-0001", "ART-0002")


def test_list_batch_article_ids_raises_for_missing_root(
    reader: LocalFolderReader, tmp_path: Path
) -> None:
    missing = tmp_path / "does-not-exist"

    with pytest.raises(SourceUnavailableError):
        reader.list_batch_article_ids(LocalBatchSource(root_path=missing))


def test_list_batch_article_ids_raises_for_a_file_not_a_directory(
    reader: LocalFolderReader, tmp_path: Path
) -> None:
    a_file = tmp_path / "not-a-dir"
    a_file.write_text("x")

    with pytest.raises(SourceUnavailableError):
        reader.list_batch_article_ids(LocalBatchSource(root_path=a_file))


def test_list_article_top_level_distinguishes_files_and_directories(
    reader: LocalFolderReader, valid_batch_root: Path
) -> None:
    source = LocalBatchSource(root_path=valid_batch_root)

    entries = reader.list_article_top_level("ART-0001", source)

    names_and_dirs = {(e.name, e.is_directory) for e in entries}
    assert ("ART-0001.xml", False) in names_and_dirs
    assert ("Original", True) in names_and_dirs
    assert ("R1", True) in names_and_dirs


def test_list_article_top_level_raises_for_missing_article(
    reader: LocalFolderReader, valid_batch_root: Path
) -> None:
    source = LocalBatchSource(root_path=valid_batch_root)

    with pytest.raises(SourceUnavailableError):
        reader.list_article_top_level("ART-NOPE", source)


def test_list_round_files_lists_recursively_with_sizes(
    reader: LocalFolderReader, valid_batch_root: Path
) -> None:
    source = LocalBatchSource(root_path=valid_batch_root)

    files = reader.list_round_files("ART-0001", "Original", source)

    by_path = {f.relative_path: f for f in files}
    assert set(by_path) == {"manuscript.txt", "fig1.txt"}
    assert by_path["manuscript.txt"].size_bytes == len(b"original manuscript content")
    assert by_path["manuscript.txt"].round_label == "Original"
    assert by_path["manuscript.txt"].checksum is None


def test_list_round_files_recurses_into_nested_subfolders(
    reader: LocalFolderReader, valid_batch_root: Path
) -> None:
    nested_dir = valid_batch_root / "ART-0001" / "Original" / "nested"
    nested_dir.mkdir()
    (nested_dir / "extra.txt").write_bytes(b"nested content")
    source = LocalBatchSource(root_path=valid_batch_root)

    files = reader.list_round_files("ART-0001", "Original", source)

    by_path = {f.relative_path: f for f in files}
    assert "nested/extra.txt" in by_path
    assert by_path["nested/extra.txt"].size_bytes == len(b"nested content")


def test_list_round_files_raises_for_missing_round(
    reader: LocalFolderReader, valid_batch_root: Path
) -> None:
    source = LocalBatchSource(root_path=valid_batch_root)

    with pytest.raises(SourceUnavailableError):
        reader.list_round_files("ART-0001", "R2-does-not-exist", source)


def test_fetch_file_copies_bytes_and_returns_matching_checksum(
    reader: LocalFolderReader, valid_batch_root: Path, tmp_path: Path
) -> None:
    source = LocalBatchSource(root_path=valid_batch_root)
    destination = tmp_path / "staged" / "manuscript.txt"
    destination.parent.mkdir(parents=True)

    checksum, size = reader.fetch_file(
        "ART-0001", "Original", "manuscript.txt", source, destination
    )

    assert destination.read_bytes() == b"original manuscript content"
    assert size == len(b"original manuscript content")

    import hashlib

    assert checksum == hashlib.sha256(b"original manuscript content").hexdigest()


def test_fetch_file_raises_for_missing_source_file(
    reader: LocalFolderReader, valid_batch_root: Path, tmp_path: Path
) -> None:
    source = LocalBatchSource(root_path=valid_batch_root)
    destination = tmp_path / "staged" / "missing.txt"
    destination.parent.mkdir(parents=True)

    with pytest.raises(SourceUnavailableError):
        reader.fetch_file("ART-0001", "Original", "does-not-exist.txt", source, destination)


def test_wrong_source_type_raises_type_error(reader: LocalFolderReader) -> None:
    wrong_source = S3BatchSource(bucket="b", prefix="p/")

    with pytest.raises(TypeError):
        reader.list_batch_article_ids(wrong_source)  # type: ignore[arg-type]
