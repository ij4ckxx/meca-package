"""Input & Staging Layer — Milestone 2.

Discovers a batch of articles from a local folder or S3 (behind a
pluggable reader interface), validates each article's structural shape
(never its XML content), and stages the referenced files into a local
working directory with integrity verification. No XML parsing, metadata
extraction, ICAM construction, or business-rule logic occurs anywhere in
this package — see 05_SYSTEM_MODULE_BREAKDOWN.md §2 and
13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md §9.4 for the design this
package implements.
"""

from __future__ import annotations

from meca_engine.input.discovery import BatchDiscovery
from meca_engine.input.models import (
    ArticleReference,
    Batch,
    BatchSource,
    DiscoveryFailure,
    FileInventory,
    FileRecord,
    LocalBatchSource,
    S3BatchSource,
    StagedArticle,
)
from meca_engine.input.staging import Stager

__all__ = [
    "ArticleReference",
    "Batch",
    "BatchDiscovery",
    "BatchSource",
    "DiscoveryFailure",
    "FileInventory",
    "FileRecord",
    "LocalBatchSource",
    "S3BatchSource",
    "Stager",
    "StagedArticle",
]
