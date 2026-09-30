"""Asset metadata extraction — Milestone 4.

Reads figure/table/supplementary-material/formula/media elements out of a
:class:`~meca_engine.extraction.parsed_model.ParsedDocument`, recognizing
them by their JATS *structural* tag name only — a schema-level fact, not
a Business Rule Book publishing-semantic judgment (that classification is
BR-078 territory, a later milestone). Reuses
:func:`~meca_engine.extraction.file_relationships.discover_file_references`,
scoped to each asset's own subtree. A pure function: no logging, no I/O,
no exceptions for missing fields.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from meca_engine.extraction.file_relationships import discover_file_references
from meca_engine.extraction.metadata_models import AssetMetadata, AssetRecord
from meca_engine.extraction.navigation import find_all, find_first, get_attribute, get_text
from meca_engine.extraction.parsed_model import EncodingInfo, ParsedDocument

if TYPE_CHECKING:
    from meca_engine.extraction.parsed_model import ParsedElement, ParseDiagnostic

DEFAULT_ASSET_TAG_NAMES: tuple[str, ...] = (
    "fig",
    "table-wrap",
    "supplementary-material",
    "disp-formula",
    "inline-formula",
    "media",
)

#: Placeholder fields for the throwaway single-subtree ``ParsedDocument``
#: built to scope :func:`discover_file_references` per asset — never
#: read for their own sake, only ``.root`` matters here.
_SCAN_SOURCE_PATH = Path("<asset-subtree-scan>")
_SCAN_ENCODING = EncodingInfo(declared_encoding=None, bom_encoding=None, effective_encoding="utf-8")


def _extract_asset(element: ParsedElement) -> AssetRecord:
    label_element = find_first(element, "label")
    scoped_document = ParsedDocument(
        source_path=_SCAN_SOURCE_PATH,
        encoding=_SCAN_ENCODING,
        doctype=None,
        root=element,
    )
    return AssetRecord(
        asset_tag=element.tag,
        element_id=get_attribute(element, "id"),
        label=get_text(label_element, recursive=True) if label_element is not None else None,
        file_references=discover_file_references(scoped_document),
    )


def extract_asset_metadata(
    document: ParsedDocument,
    *,
    asset_tag_names: tuple[str, ...] = DEFAULT_ASSET_TAG_NAMES,
) -> tuple[AssetMetadata, tuple[ParseDiagnostic, ...]]:
    """Extract structural asset metadata from a parsed document.

    Args:
        document: The parsed document to read from.
        asset_tag_names: Which local tag names count as a recognized
            asset. Defaults to the common JATS structural set (figure,
            table, supplementary material, formulas, media).

    Returns:
        The extracted
        :class:`~meca_engine.extraction.metadata_models.AssetMetadata`,
        alongside an always-empty diagnostics tuple.
    """
    assets = tuple(
        _extract_asset(element)
        for tag_name in asset_tag_names
        for element in find_all(document.root, tag_name)
    )
    return AssetMetadata(assets=assets), ()
