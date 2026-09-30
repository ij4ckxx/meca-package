"""Package Builder — atomic MECA package assembly (Milestone 7; ADR-017).

Consumes the outputs of the existing 5 XML generators and the ICAM's
``resolved_files``/manifest.xml to produce one complete, atomically
published ``MECA_<ArticleID>.zip``. See
:class:`meca_engine.packaging.builder.PackageBuilder` for the single
orchestration entry point.
"""

from __future__ import annotations

from meca_engine.packaging.asset_copy import AssetCopyService
from meca_engine.packaging.batch_runner import (
    PackageBatchRunner,
    PackageOutcome,
    PackageOutcomeStatus,
)
from meca_engine.packaging.builder import PackageBuilder
from meca_engine.packaging.models import (
    AssetCopyReport,
    GeneratedDocumentSet,
    PackagedFile,
    StagedPackage,
)
from meca_engine.packaging.zip_builder import ZipBuilder

__all__ = [
    "AssetCopyReport",
    "AssetCopyService",
    "GeneratedDocumentSet",
    "PackageBatchRunner",
    "PackageBuilder",
    "PackageOutcome",
    "PackageOutcomeStatus",
    "PackagedFile",
    "StagedPackage",
    "ZipBuilder",
]
