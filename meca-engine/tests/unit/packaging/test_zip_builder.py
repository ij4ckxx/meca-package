"""Unit tests for meca_engine.packaging.zip_builder.ZipBuilder."""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

import pytest

from meca_engine.exceptions.article_errors import PackageAssemblyError
from meca_engine.logging_ import get_logger
from meca_engine.packaging.zip_builder import ZipBuilder

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def _builder(compression: str = "deflated") -> ZipBuilder:
    return ZipBuilder(
        compression=compression, compresslevel=6, logger=get_logger("test.zip_builder")
    )


def _populate(source_root: Path) -> None:
    source_root.mkdir()
    (source_root / "b_article.xml").write_bytes(b"<article/>")
    (source_root / "a_raw.xml").write_bytes(b"<raw/>")
    (source_root / "files").mkdir()
    (source_root / "files" / "R1").mkdir()
    (source_root / "files" / "R1" / "fig1.jpg").write_bytes(b"\x00\x01\x02")


def test_build_includes_every_file_with_relative_arcnames(tmp_path: Path) -> None:
    source_root = tmp_path / "staging"
    _populate(source_root)
    zip_path = tmp_path / "out.zip"

    _builder().build(source_root=source_root, zip_path=zip_path, article_id="ART-1")

    with zipfile.ZipFile(zip_path) as archive:
        assert set(archive.namelist()) == {"a_raw.xml", "b_article.xml", "files/R1/fig1.jpg"}
        assert archive.read("files/R1/fig1.jpg") == b"\x00\x01\x02"


def test_build_orders_entries_deterministically(tmp_path: Path) -> None:
    source_root = tmp_path / "staging"
    _populate(source_root)
    zip_path = tmp_path / "out.zip"

    _builder().build(source_root=source_root, zip_path=zip_path, article_id="ART-1")

    with zipfile.ZipFile(zip_path) as archive:
        assert archive.namelist() == ["a_raw.xml", "b_article.xml", "files/R1/fig1.jpg"]


def test_build_produces_byte_identical_output_across_runs(tmp_path: Path) -> None:
    source_root = tmp_path / "staging"
    _populate(source_root)
    zip_path_1 = tmp_path / "out1.zip"
    zip_path_2 = tmp_path / "out2.zip"

    _builder().build(source_root=source_root, zip_path=zip_path_1, article_id="ART-1")
    _builder().build(source_root=source_root, zip_path=zip_path_2, article_id="ART-1")

    assert zip_path_1.read_bytes() == zip_path_2.read_bytes()


def test_build_with_stored_compression_is_uncompressed(tmp_path: Path) -> None:
    source_root = tmp_path / "staging"
    _populate(source_root)
    zip_path = tmp_path / "out.zip"

    _builder("stored").build(source_root=source_root, zip_path=zip_path, article_id="ART-1")

    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            assert info.compress_type == zipfile.ZIP_STORED


def test_build_creates_parent_directory_of_zip_path(tmp_path: Path) -> None:
    source_root = tmp_path / "staging"
    _populate(source_root)
    zip_path = tmp_path / "nested" / "dir" / "out.zip"

    _builder().build(source_root=source_root, zip_path=zip_path, article_id="ART-1")

    assert zip_path.exists()


def test_unrecognized_compression_raises_at_construction(tmp_path: Path) -> None:
    with pytest.raises(PackageAssemblyError):
        ZipBuilder(compression="bzip2", compresslevel=None, logger=get_logger("test.zip_builder"))
