"""Unit tests for meca_engine.packaging.asset_copy.AssetCopyService."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from meca_engine.exceptions.article_errors import PackageAssemblyError
from meca_engine.logging_ import get_logger
from meca_engine.packaging.asset_copy import AssetCopyService
from meca_engine.packaging.models import PackagedFile

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def _checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _service(overwrite_policy: str = "fail") -> AssetCopyService:
    return AssetCopyService(overwrite_policy=overwrite_policy, logger=get_logger("test.asset_copy"))


def _make_source(tmp_path: Path, name: str, content: bytes) -> Path:
    source_dir = tmp_path / "sources"
    source_dir.mkdir(exist_ok=True)
    source_path = source_dir / name
    source_path.write_bytes(content)
    return source_path


def test_copy_all_copies_a_single_file_to_its_href(tmp_path: Path) -> None:
    content = b"figure bytes"
    source_path = _make_source(tmp_path, "fig1.jpg", content)
    entry = PackagedFile(
        href="files/R1/fig1.jpg",
        source_path=source_path,
        checksum=_checksum(content),
        size_bytes=len(content),
    )
    destination_root = tmp_path / "package"

    report = _service().copy_all((entry,), destination_root=destination_root, article_id="ART-1")

    assert report.copied == (entry,)
    assert report.skipped == ()
    assert report.duplicate_hrefs == ()
    assert (destination_root / "files" / "R1" / "fig1.jpg").read_bytes() == content


def test_copy_all_preserves_source_mtime(tmp_path: Path) -> None:
    content = b"data"
    source_path = _make_source(tmp_path, "a.pdf", content)
    entry = PackagedFile(
        href="files/Original/a.pdf",
        source_path=source_path,
        checksum=_checksum(content),
        size_bytes=len(content),
    )
    destination_root = tmp_path / "package"

    _service().copy_all((entry,), destination_root=destination_root, article_id="ART-1")

    destination_path = destination_root / "files" / "Original" / "a.pdf"
    assert destination_path.stat().st_mtime == pytest.approx(source_path.stat().st_mtime)


def test_copy_all_raises_for_missing_source_file(tmp_path: Path) -> None:
    entry = PackagedFile(
        href="files/R1/missing.jpg",
        source_path=tmp_path / "does-not-exist.jpg",
        checksum="irrelevant",
        size_bytes=0,
    )

    with pytest.raises(PackageAssemblyError) as exc_info:
        _service().copy_all((entry,), destination_root=tmp_path / "package", article_id="ART-1")

    assert exc_info.value.retryable is False


def test_copy_all_detects_duplicate_hrefs_without_double_copying(tmp_path: Path) -> None:
    content = b"content"
    source_path = _make_source(tmp_path, "dup.jpg", content)
    entry = PackagedFile(
        href="files/R1/dup.jpg",
        source_path=source_path,
        checksum=_checksum(content),
        size_bytes=len(content),
    )
    destination_root = tmp_path / "package"

    report = _service().copy_all(
        (entry, entry), destination_root=destination_root, article_id="ART-1"
    )

    assert report.copied == (entry,)
    assert report.duplicate_hrefs == ("files/R1/dup.jpg",)


def test_copy_all_fails_on_existing_destination_under_fail_policy(tmp_path: Path) -> None:
    content = b"content"
    source_path = _make_source(tmp_path, "a.jpg", content)
    entry = PackagedFile(
        href="files/R1/a.jpg",
        source_path=source_path,
        checksum=_checksum(content),
        size_bytes=len(content),
    )
    destination_root = tmp_path / "package"
    destination_path = destination_root / "files" / "R1" / "a.jpg"
    destination_path.parent.mkdir(parents=True)
    destination_path.write_bytes(b"pre-existing")

    with pytest.raises(PackageAssemblyError):
        _service("fail").copy_all((entry,), destination_root=destination_root, article_id="ART-1")


def test_copy_all_skips_existing_destination_under_skip_policy(tmp_path: Path) -> None:
    content = b"content"
    source_path = _make_source(tmp_path, "a.jpg", content)
    entry = PackagedFile(
        href="files/R1/a.jpg",
        source_path=source_path,
        checksum=_checksum(content),
        size_bytes=len(content),
    )
    destination_root = tmp_path / "package"
    destination_path = destination_root / "files" / "R1" / "a.jpg"
    destination_path.parent.mkdir(parents=True)
    destination_path.write_bytes(b"pre-existing")

    report = _service("skip").copy_all(
        (entry,), destination_root=destination_root, article_id="ART-1"
    )

    assert report.copied == ()
    assert report.skipped == (entry,)
    assert destination_path.read_bytes() == b"pre-existing"


def test_copy_all_overwrites_existing_destination_under_overwrite_policy(tmp_path: Path) -> None:
    content = b"new content"
    source_path = _make_source(tmp_path, "a.jpg", content)
    entry = PackagedFile(
        href="files/R1/a.jpg",
        source_path=source_path,
        checksum=_checksum(content),
        size_bytes=len(content),
    )
    destination_root = tmp_path / "package"
    destination_path = destination_root / "files" / "R1" / "a.jpg"
    destination_path.parent.mkdir(parents=True)
    destination_path.write_bytes(b"stale")

    report = _service("overwrite").copy_all(
        (entry,), destination_root=destination_root, article_id="ART-1"
    )

    assert report.copied == (entry,)
    assert destination_path.read_bytes() == content


def test_copy_all_raises_and_removes_partial_file_on_checksum_mismatch(tmp_path: Path) -> None:
    content = b"actual content"
    source_path = _make_source(tmp_path, "a.jpg", content)
    entry = PackagedFile(
        href="files/R1/a.jpg",
        source_path=source_path,
        checksum="0" * 64,  # deliberately wrong
        size_bytes=len(content),
    )
    destination_root = tmp_path / "package"

    with pytest.raises(PackageAssemblyError) as exc_info:
        _service().copy_all((entry,), destination_root=destination_root, article_id="ART-1")

    assert exc_info.value.retryable is True
    assert not (destination_root / "files" / "R1" / "a.jpg").exists()


def test_copy_all_creates_nested_round_directories(tmp_path: Path) -> None:
    content = b"nested"
    source_path = _make_source(tmp_path, "b.docx", content)
    entry = PackagedFile(
        href="files/Original/b.docx",
        source_path=source_path,
        checksum=_checksum(content),
        size_bytes=len(content),
    )
    destination_root = tmp_path / "package"

    _service().copy_all((entry,), destination_root=destination_root, article_id="ART-1")

    assert (destination_root / "files" / "Original").is_dir()
