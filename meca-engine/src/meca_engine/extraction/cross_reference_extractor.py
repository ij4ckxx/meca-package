"""Cross-reference extraction — Milestone 4.

Reads every ``xref``-style cross-reference and builds a compact id index
out of a :class:`~meca_engine.extraction.parsed_model.ParsedDocument`.
Reuses :func:`~meca_engine.extraction.navigation.build_id_index` and the
Milestone 3 diagnostic producers
(:func:`~meca_engine.extraction.diagnostics.find_duplicate_ids`,
:func:`~meca_engine.extraction.diagnostics.find_malformed_references`).
Preserves relationships only — never validates whether a reference makes
publishing sense, never reconstructs anything beyond what the source
literally encodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.extraction.diagnostics import find_duplicate_ids, find_malformed_references
from meca_engine.extraction.metadata_models import CrossReferenceMap, ReferenceRecord
from meca_engine.extraction.navigation import build_id_index, find_all, get_attribute

if TYPE_CHECKING:
    from meca_engine.extraction.parsed_model import ParsedDocument, ParseDiagnostic

DEFAULT_ID_ATTRIBUTE_NAMES: tuple[str, ...] = ("id",)
DEFAULT_REFERENCE_ATTRIBUTE_NAMES: tuple[str, ...] = ("rid",)


def extract_cross_references(
    document: ParsedDocument,
    *,
    id_attribute_names: tuple[str, ...] = DEFAULT_ID_ATTRIBUTE_NAMES,
    reference_attribute_names: tuple[str, ...] = DEFAULT_REFERENCE_ATTRIBUTE_NAMES,
) -> tuple[CrossReferenceMap, tuple[ParseDiagnostic, ...]]:
    """Extract cross-reference relationships from a parsed document.

    Args:
        document: The parsed document to read from.
        id_attribute_names: Which unprefixed attribute names count as an
            "id". Forwarded to
            :func:`~meca_engine.extraction.navigation.build_id_index` and
            :func:`~meca_engine.extraction.diagnostics.find_duplicate_ids`.
        reference_attribute_names: Which unprefixed attribute names count
            as holding a reference. Forwarded to
            :func:`~meca_engine.extraction.diagnostics.find_malformed_references`.

    Returns:
        The extracted
        :class:`~meca_engine.extraction.metadata_models.CrossReferenceMap`,
        alongside diagnostics for any duplicate id or malformed reference
        found (dangling-reference diagnostics are Milestone 3's
        :func:`~meca_engine.extraction.diagnostics.find_dangling_references`
        concern, not repeated here).
    """
    id_index = build_id_index(document.root, id_attribute_names=id_attribute_names)
    compact_id_index = tuple((value, element.tag) for value, element in id_index.items())

    references: list[ReferenceRecord] = []
    for element in find_all(document.root, "xref"):
        for attribute_name in reference_attribute_names:
            raw_value = get_attribute(element, attribute_name)
            if raw_value is None:
                continue
            references.append(
                ReferenceRecord(
                    referencing_tag=element.tag,
                    referencing_ref_type=get_attribute(element, "ref-type"),
                    attribute_name=attribute_name,
                    target_ids=tuple(raw_value.split()),
                )
            )

    diagnostics = find_duplicate_ids(
        document.root, id_attribute_names=id_attribute_names
    ) + find_malformed_references(
        document.root, reference_attribute_names=reference_attribute_names
    )

    return CrossReferenceMap(id_index=compact_id_index, references=tuple(references)), diagnostics
