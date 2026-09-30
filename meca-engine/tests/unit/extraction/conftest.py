"""Shared fixtures for the XML Parsing Layer unit tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@pytest.fixture
def write_xml(tmp_path: Path) -> Callable[[bytes, str], Path]:
    """Return a helper that writes raw bytes to a uniquely-named XML file."""

    def _write(content: bytes, filename: str = "test.xml") -> Path:
        path = tmp_path / filename
        path.write_bytes(content)
        return path

    return _write
