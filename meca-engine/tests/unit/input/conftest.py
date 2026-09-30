"""Shared fixtures for the Input & Staging Layer unit tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


@pytest.fixture
def batch_root_missing_xml(tmp_path: Path) -> Path:
    """A batch root whose single article has no root-level XML file."""
    root = tmp_path / "batch"
    _write(root / "ART-BAD" / "Original" / "manuscript.txt", b"content")
    return root


@pytest.fixture
def batch_root_duplicate_xml(tmp_path: Path) -> Path:
    """A batch root whose single article has two root-level XML files."""
    root = tmp_path / "batch"
    _write(root / "ART-BAD" / "ART-BAD.xml", b"<article/>")
    _write(root / "ART-BAD" / "ART-BAD-copy.xml", b"<article/>")
    _write(root / "ART-BAD" / "Original" / "manuscript.txt", b"content")
    return root


@pytest.fixture
def batch_root_no_rounds(tmp_path: Path) -> Path:
    """A batch root whose single article has a root XML but zero round folders."""
    root = tmp_path / "batch"
    _write(root / "ART-BAD" / "ART-BAD.xml", b"<article/>")
    return root


@pytest.fixture
def batch_root_with_anomalies(tmp_path: Path) -> Path:
    """A batch root whose article has a zero-byte file and an OS-artifact file."""
    root = tmp_path / "batch"
    _write(root / "ART-0001" / "ART-0001.xml", b"<article/>")
    _write(root / "ART-0001" / "Original" / "manuscript.txt", b"content")
    _write(root / "ART-0001" / "Original" / "empty.txt", b"")
    _write(root / "ART-0001" / "Original" / ".DS_Store", b"junk")
    return root
