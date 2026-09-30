"""XML Parsing, Metadata Extraction & ICAM-adjacent Resolution — Milestones 3-5B.

Milestone 3 converts source XML files into strongly-typed, immutable
parsed objects that closely mirror the source document's structure.
Milestone 4 extracts structured metadata from those parsed objects.
Milestone 5B adds this package's three ICAM-adjacent resolution/
classification modules (`custom_meta_classifier`, `round_resolver`,
`file_resolver`), per 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.3-4.5 —
these do reference `meca_engine.model` types (the layering permits
`extraction` to depend on `model`), but still apply no business-rule
*transformation* of values, only classification/resolution into already-
approved ICAM shapes. See :mod:`meca_engine.extraction.parsed_model` and
:mod:`meca_engine.extraction.metadata_models` module docstrings for the
generic, no-ICAM-reference boundary Milestones 3-4's own modules respect.

Business-rule-driven transformation (`transform.*`), MECA XML generation,
and everything downstream remain deferred to Milestone 6+ — see
`08_IMPLEMENTATION_ROADMAP.md` Phase 3.
"""

from __future__ import annotations

from meca_engine.extraction.article_metadata_extractor import extract_article_metadata
from meca_engine.extraction.asset_metadata_extractor import (
    DEFAULT_ASSET_TAG_NAMES,
    extract_asset_metadata,
)
from meca_engine.extraction.contributor_metadata_extractor import extract_contributor_metadata
from meca_engine.extraction.cross_reference_extractor import extract_cross_references
from meca_engine.extraction.custom_meta_classifier import classify as classify_custom_metadata
from meca_engine.extraction.custom_metadata_extractor import extract_custom_metadata
from meca_engine.extraction.diagnostics import (
    find_dangling_references,
    find_duplicate_ids,
    find_malformed_references,
)
from meca_engine.extraction.file_relationships import (
    DEFAULT_REFERENCE_ATTRIBUTES,
    XLINK_NAMESPACE_URI,
    FileReference,
    discover_file_references,
)
from meca_engine.extraction.file_resolver import resolve_files
from meca_engine.extraction.journal_metadata_extractor import extract_journal_metadata
from meca_engine.extraction.metadata_extraction import extract_all_metadata
from meca_engine.extraction.metadata_models import (
    AffiliationRecord,
    ArticleIdentifier,
    ArticleMetadata,
    AssetMetadata,
    AssetRecord,
    ContributorMetadata,
    ContributorRecord,
    CrossReferenceMap,
    CustomMetadata,
    CustomMetaEntry,
    DateRecord,
    ExtractionBundle,
    JournalMetadata,
    NamedContentField,
    ReferenceRecord,
    WorkflowEventRecord,
    WorkflowMetadata,
)
from meca_engine.extraction.navigation import (
    as_bool,
    as_float,
    as_int,
    build_id_index,
    find_all,
    find_by_path,
    find_first,
    get_attribute,
    get_text,
    iter_descendants,
)
from meca_engine.extraction.parsed_model import (
    DiagnosticCategory,
    DiagnosticSeverity,
    DoctypeDeclaration,
    EncodingInfo,
    NamespaceDeclaration,
    ParsedAttribute,
    ParsedDocument,
    ParsedElement,
    ParseDiagnostic,
    SourceLocation,
)
from meca_engine.extraction.round_resolver import resolve_rounds
from meca_engine.extraction.workflow_metadata_extractor import (
    DEFAULT_EVENT_TAG_NAMES,
    extract_workflow_metadata,
)
from meca_engine.extraction.xml_loader import XmlLoader

__all__ = [
    "DEFAULT_ASSET_TAG_NAMES",
    "DEFAULT_EVENT_TAG_NAMES",
    "DEFAULT_REFERENCE_ATTRIBUTES",
    "XLINK_NAMESPACE_URI",
    "AffiliationRecord",
    "ArticleIdentifier",
    "ArticleMetadata",
    "AssetMetadata",
    "AssetRecord",
    "ContributorMetadata",
    "ContributorRecord",
    "CrossReferenceMap",
    "CustomMetaEntry",
    "CustomMetadata",
    "DateRecord",
    "DiagnosticCategory",
    "DiagnosticSeverity",
    "DoctypeDeclaration",
    "EncodingInfo",
    "ExtractionBundle",
    "FileReference",
    "JournalMetadata",
    "NamedContentField",
    "NamespaceDeclaration",
    "ParseDiagnostic",
    "ParsedAttribute",
    "ParsedDocument",
    "ParsedElement",
    "ReferenceRecord",
    "SourceLocation",
    "WorkflowEventRecord",
    "WorkflowMetadata",
    "XmlLoader",
    "as_bool",
    "as_float",
    "as_int",
    "build_id_index",
    "classify_custom_metadata",
    "discover_file_references",
    "extract_all_metadata",
    "extract_article_metadata",
    "extract_asset_metadata",
    "extract_contributor_metadata",
    "extract_cross_references",
    "extract_custom_metadata",
    "extract_journal_metadata",
    "extract_workflow_metadata",
    "find_all",
    "find_by_path",
    "find_dangling_references",
    "find_duplicate_ids",
    "find_first",
    "find_malformed_references",
    "get_attribute",
    "get_text",
    "iter_descendants",
    "resolve_files",
    "resolve_rounds",
]
