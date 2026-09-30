"""Unit tests for meca_engine.generators.manifest_xml.checksums.

Interface-only module (see its own docstring): these tests confirm the
one currently-supported algorithm behaves correctly in isolation — never
that it is invoked anywhere in `ManifestXmlGenerator._generate` (it
deliberately is not; see `test_generator.py`'s absence of any checksum
assertion on the produced XML).
"""

from __future__ import annotations

import pytest

from meca_engine.generators.manifest_xml.checksums import (
    DEFAULT_CHECKSUM_ALGORITHM,
    Sha256PassthroughChecksum,
)
from meca_engine.model.article import ResolvedFile

pytestmark = pytest.mark.unit


def _resolved_file(checksum: str) -> ResolvedFile:
    return ResolvedFile(
        round_label="R1",
        category="manuscript",
        original_filename="manuscript.docx",
        staged_physical_path="/staged/R1/manuscript.docx",
        checksum=checksum,
        size_bytes=1024,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def test_sha256_passthrough_returns_the_icam_checksum_unchanged() -> None:
    algorithm = Sha256PassthroughChecksum()
    resolved_file = _resolved_file("a" * 64)

    assert algorithm.compute(resolved_file) == "a" * 64


def test_default_checksum_algorithm_is_the_sha256_passthrough() -> None:
    resolved_file = _resolved_file("b" * 64)

    assert DEFAULT_CHECKSUM_ALGORITHM.compute(resolved_file) == "b" * 64
