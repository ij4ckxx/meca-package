"""Unit tests for meca_engine.validation.package_validator.validate_staged_package."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from meca_engine.packaging.models import PackageStatus, StagedPackage
from meca_engine.validation.package_validator import validate_staged_package

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def _staged_package(zip_path: Path, xml_filenames: tuple[str, ...] = ()) -> StagedPackage:
    return StagedPackage(
        article_id="cs-2025-0001",
        zip_path=zip_path,
        doi=None,
        packaged_files=(),
        xml_filenames=xml_filenames,
        status=PackageStatus.CERTIFIED,
    )


def test_never_raises_when_zip_is_missing(tmp_path: Path) -> None:
    """Regression: a real, already-built package must never become ENGINE_FAILURE just
    because this best-effort re-validation step can't reopen it."""
    staged = _staged_package(tmp_path / "does-not-exist.zip", ("cs-2025-0001_article.xml",))

    report = validate_staged_package(staged)

    assert report.article_id == "cs-2025-0001"
    assert report.files == ()


def test_never_raises_when_zip_is_corrupt(tmp_path: Path) -> None:
    zip_path = tmp_path / "corrupt.zip"
    zip_path.write_bytes(b"not a real zip file")
    staged = _staged_package(zip_path, ("cs-2025-0001_article.xml",))

    report = validate_staged_package(staged)

    assert report.files == ()
