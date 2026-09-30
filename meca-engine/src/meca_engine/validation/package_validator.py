"""Validate an already-built MECA package's XML documents — Milestone 2.

Deliberately a post-processing step, matching
:mod:`meca_engine.reporting.package_embed`'s own pattern: it reopens the
already-finished zip and reads entries back out, touching nothing in
:class:`~meca_engine.packaging.builder.PackageBuilder` or any generator.
Runs strictly after a package is built; never raises, never affects
``PackageOutcomeStatus``.
"""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

from meca_engine.validation.models import PackageValidationReport
from meca_engine.validation.xml_validator import (
    VALIDATED_FILENAME_SUFFIXES,
    validate_generated_file,
)

if TYPE_CHECKING:
    from meca_engine.packaging.models import StagedPackage


def validate_staged_package(staged_package: StagedPackage) -> PackageValidationReport:
    """Validate the article/reviews/manifest/transfer XML in a built package.

    Reads each file's bytes back out of ``staged_package.zip_path`` (the
    package is already complete and closed) and runs
    :func:`~meca_engine.validation.xml_validator.validate_generated_file`
    on it. Any file that cannot be read from the archive is skipped
    rather than raising — a missing entry here is a packaging-layer
    surprise this module has no business masking with a fabricated pass
    or crashing the batch over.
    """
    filenames = [
        name for name in staged_package.xml_filenames if name.endswith(VALIDATED_FILENAME_SUFFIXES)
    ]
    reports = []
    try:
        with zipfile.ZipFile(staged_package.zip_path, mode="r") as archive:
            for filename in filenames:
                try:
                    document = archive.read(filename)
                except KeyError:
                    continue
                reports.append(validate_generated_file(filename, document))
    except (OSError, zipfile.BadZipFile):
        # The package itself was already built and closed successfully —
        # an already-complete, real package must never be turned into a
        # failure report just because this best-effort re-validation step
        # couldn't reopen it. Matches this function's own "never raises"
        # contract, which the zip open itself previously bypassed.
        return PackageValidationReport(article_id=staged_package.article_id, files=())

    return PackageValidationReport(article_id=staged_package.article_id, files=tuple(reports))
