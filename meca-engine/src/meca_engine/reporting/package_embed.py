"""Embed conversion-report.json into an already-built MECA package — Milestone 13.

Deliberately a post-processing step, not a :class:`~meca_engine.packaging.builder.PackageBuilder`
change: the Conversion Report can only be built *after* `PackageBuilder.build()`
returns (it summarizes that very build), so embedding it inside the same
zip means reopening the already-finished archive and appending one more
entry. No XML content, no existing zip entry, and no
`PackageBuilder`/generator behavior is touched.
"""

from __future__ import annotations

import json
import zipfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.packaging.conversion_report import ConversionReport

_ENTRY_NAME = "conversion-report.json"


def embed_conversion_report(zip_path: Path, report: ConversionReport) -> None:
    """Append ``conversion-report.json`` to an existing MECA package zip.

    Args:
        zip_path: The already-written ``MECA_<ArticleID>.zip``.
        report: The Conversion Report describing exactly how this
            package was generated.
    """
    payload = json.dumps(report.to_dict(), indent=2)
    with zipfile.ZipFile(zip_path, mode="a", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(_ENTRY_NAME, payload)
