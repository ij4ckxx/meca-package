"""Unit tests for meca_engine.input.discovery.BatchDiscovery."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from meca_engine.input.discovery import BatchDiscovery
from meca_engine.input.models import LocalBatchSource
from meca_engine.input.readers.local_reader import LocalFolderReader
from meca_engine.logging_ import get_logger

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


@pytest.fixture
def discovery() -> BatchDiscovery:
    return BatchDiscovery(LocalFolderReader(), get_logger("test.discovery"))


def test_discovers_all_valid_articles(discovery: BatchDiscovery, valid_batch_root: Path) -> None:
    batch = discovery.discover(LocalBatchSource(root_path=valid_batch_root), batch_id="b1")

    assert {ref.article_id for ref in batch.article_refs} == {"ART-0001", "ART-0002"}
    assert batch.discovery_failures == ()

    art1 = next(ref for ref in batch.article_refs if ref.article_id == "ART-0001")
    assert art1.root_xml_relative_name == "ART-0001.xml"
    assert set(art1.file_inventory.round_labels) == {"Original", "R1"}
    assert len(art1.file_inventory.files) == 3  # 2 in Original, 1 in R1


def test_missing_root_xml_recorded_as_discovery_failure(
    discovery: BatchDiscovery, batch_root_missing_xml: Path
) -> None:
    batch = discovery.discover(LocalBatchSource(root_path=batch_root_missing_xml), batch_id="b1")

    assert batch.article_refs == ()
    assert len(batch.discovery_failures) == 1
    failure = batch.discovery_failures[0]
    assert failure.article_id == "ART-BAD"
    assert failure.exception_type == "InvalidArticlePackageError"


def test_duplicate_root_xml_recorded_as_discovery_failure(
    discovery: BatchDiscovery, batch_root_duplicate_xml: Path
) -> None:
    batch = discovery.discover(LocalBatchSource(root_path=batch_root_duplicate_xml), batch_id="b1")

    assert batch.article_refs == ()
    assert len(batch.discovery_failures) == 1
    assert batch.discovery_failures[0].exception_type == "InvalidArticlePackageError"


def test_no_round_folders_recorded_as_discovery_failure(
    discovery: BatchDiscovery, batch_root_no_rounds: Path
) -> None:
    batch = discovery.discover(LocalBatchSource(root_path=batch_root_no_rounds), batch_id="b1")

    assert batch.article_refs == ()
    assert len(batch.discovery_failures) == 1
    assert batch.discovery_failures[0].exception_type == "InvalidArticlePackageError"


def test_one_bad_article_does_not_block_discovery_of_others(
    discovery: BatchDiscovery, tmp_path: Path
) -> None:
    root = tmp_path / "batch"
    (root / "ART-GOOD").mkdir(parents=True)
    (root / "ART-GOOD" / "ART-GOOD.xml").write_bytes(b"<article/>")
    (root / "ART-GOOD" / "Original").mkdir()
    (root / "ART-GOOD" / "Original" / "manuscript.txt").write_bytes(b"content")
    (root / "ART-BAD").mkdir()  # no xml, no rounds

    batch = discovery.discover(LocalBatchSource(root_path=root), batch_id="b1")

    assert {ref.article_id for ref in batch.article_refs} == {"ART-GOOD"}
    assert {f.article_id for f in batch.discovery_failures} == {"ART-BAD"}


def test_anomalous_files_flagged_but_not_fatal(
    discovery: BatchDiscovery, batch_root_with_anomalies: Path
) -> None:
    batch = discovery.discover(LocalBatchSource(root_path=batch_root_with_anomalies), batch_id="b1")

    assert batch.discovery_failures == ()
    art = batch.article_refs[0]
    assert "Original/empty.txt" in art.file_inventory.anomalous_relative_paths
    assert "Original/.DS_Store" in art.file_inventory.anomalous_relative_paths
    # The anomalous files are still part of the inventory, not silently dropped.
    assert any(f.relative_path == "empty.txt" for f in art.file_inventory.files)


def test_duplicate_filename_within_round_raises_discovery_failure(
    discovery: BatchDiscovery, tmp_path: Path
) -> None:
    # Simulate a duplicate by using a case-insensitive collision, which two
    # different real filesystems could both produce from a single, valid
    # source listing (e.g. case-insensitive local disk vs. case-sensitive
    # object store round-tripped through a case-folding intermediary).
    root = tmp_path / "batch"
    (root / "ART-0001" / "Original").mkdir(parents=True)
    (root / "ART-0001" / "ART-0001.xml").write_bytes(b"<article/>")
    (root / "ART-0001" / "Original" / "manuscript.txt").write_bytes(b"content")

    from meca_engine.input.models import FileRecord
    from meca_engine.input.readers.base import InputReader

    class _DuplicatingReader(InputReader):
        """Wraps a real reader but injects a duplicate (case-insensitive) filename."""

        def __init__(self, delegate: InputReader) -> None:
            self._delegate = delegate

        def list_batch_article_ids(self, source):  # type: ignore[no-untyped-def]
            return self._delegate.list_batch_article_ids(source)

        def list_article_top_level(self, article_id, source):  # type: ignore[no-untyped-def]
            return self._delegate.list_article_top_level(article_id, source)

        def list_round_files(self, article_id, round_label, source):  # type: ignore[no-untyped-def]
            real = self._delegate.list_round_files(article_id, round_label, source)
            duplicate = FileRecord(
                round_label=round_label, relative_path="MANUSCRIPT.TXT", size_bytes=1
            )
            return (*real, duplicate)

        def fetch_file(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return self._delegate.fetch_file(*args, **kwargs)

    from meca_engine.input.readers.local_reader import LocalFolderReader

    injecting_reader = _DuplicatingReader(LocalFolderReader())
    injecting_discovery = BatchDiscovery(injecting_reader, get_logger("test.discovery.dup"))

    batch = injecting_discovery.discover(LocalBatchSource(root_path=root), batch_id="b1")

    assert batch.article_refs == ()
    assert batch.discovery_failures[0].exception_type == "DuplicateFileError"


def test_duplicate_article_id_within_one_scan_recorded_as_failure(
    discovery: BatchDiscovery, valid_batch_root: Path
) -> None:
    from meca_engine.input.readers.base import InputReader

    class _DuplicatingIdsReader(InputReader):
        def __init__(self, delegate: InputReader) -> None:
            self._delegate = delegate

        def list_batch_article_ids(self, source):  # type: ignore[no-untyped-def]
            real = self._delegate.list_batch_article_ids(source)
            return (*real, real[0])  # duplicate the first id

        def list_article_top_level(self, article_id, source):  # type: ignore[no-untyped-def]
            return self._delegate.list_article_top_level(article_id, source)

        def list_round_files(self, article_id, round_label, source):  # type: ignore[no-untyped-def]
            return self._delegate.list_round_files(article_id, round_label, source)

        def fetch_file(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return self._delegate.fetch_file(*args, **kwargs)

    injecting_reader = _DuplicatingIdsReader(LocalFolderReader())
    injecting_discovery = BatchDiscovery(injecting_reader, get_logger("test.discovery.dupid"))

    batch = injecting_discovery.discover(
        LocalBatchSource(root_path=valid_batch_root), batch_id="b1"
    )

    assert len(batch.article_refs) == 2  # ART-0001, ART-0002 each discovered once
    duplicate_failures = [
        f for f in batch.discovery_failures if f.exception_type == "DuplicateArticleError"
    ]
    assert len(duplicate_failures) == 1
    assert duplicate_failures[0].article_id == "ART-0001"
