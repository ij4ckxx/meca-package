"""Parse diagnostic producers.

The diagnostic *data types* (``ParseDiagnostic``, ``DiagnosticSeverity``,
``DiagnosticCategory``) live in
:mod:`meca_engine.extraction.parsed_model`, alongside the rest of the
Parsed Object Model they attach to. This module holds the (currently one)
non-trivial diagnostic-*producing* check that isn't naturally part of
loading itself: detecting dangling internal cross-references.

Generic, not JATS-specific: which attribute names count as a "reference"
(or an "id") is a caller-supplied parameter, not a hard-coded assumption
about any particular XML vocabulary's tag/attribute semantics.

``find_duplicate_ids`` and ``find_malformed_references`` were added in
Milestone 4 (Metadata Extraction Layer), reusing the exact same
diagnostic mechanism as ``find_dangling_references`` (Milestone 3) — no
new diagnostic-reporting concept was introduced.
"""

from __future__ import annotations

from meca_engine.extraction.navigation import (
    XML_NAMESPACE_URI,
    build_id_index,
    iter_descendants,
)
from meca_engine.extraction.parsed_model import (
    DiagnosticCategory,
    DiagnosticSeverity,
    ParsedElement,
    ParseDiagnostic,
)

_DEFAULT_REFERENCE_ATTRIBUTE_NAMES: tuple[str, ...] = ("rid",)
_DEFAULT_ID_ATTRIBUTE_NAMES: tuple[str, ...] = ("id",)


def find_dangling_references(
    root: ParsedElement,
    *,
    reference_attribute_names: tuple[str, ...] = _DEFAULT_REFERENCE_ATTRIBUTE_NAMES,
    id_attribute_names: tuple[str, ...] = ("id",),
) -> tuple[ParseDiagnostic, ...]:
    """Find attribute values that reference an id not present anywhere in the document.

    A "reference" attribute's value is treated as a whitespace-separated
    list of id tokens (matching the common IDREFS convention — a single
    id is simply a one-token list), each checked against every id-bearing
    element found via
    :func:`meca_engine.extraction.navigation.build_id_index`.

    Args:
        root: The subtree to scan.
        reference_attribute_names: Which unprefixed attribute names count
            as holding a reference to look up. Defaults to ``("rid",)`` —
            a widely-used convention (not exclusive to any one XML
            vocabulary), not a hard-coded assumption; pass a different
            set for a different document dialect.
        id_attribute_names: Forwarded to
            :func:`~meca_engine.extraction.navigation.build_id_index`.

    Returns:
        One WARNING-severity, ``MISSING_REFERENCE``-category diagnostic
        per dangling reference token found, in document order.
    """
    id_index = build_id_index(root, id_attribute_names=id_attribute_names)
    diagnostics: list[ParseDiagnostic] = []
    for element in iter_descendants(root):
        for attribute in element.attributes:
            if (
                attribute.namespace_uri is not None
                or attribute.name not in reference_attribute_names
            ):
                continue
            for token in attribute.value.split():
                if token not in id_index:
                    diagnostics.append(
                        ParseDiagnostic(
                            severity=DiagnosticSeverity.WARNING,
                            category=DiagnosticCategory.MISSING_REFERENCE,
                            message=(
                                f"Element <{element.tag}> attribute {attribute.name!r} "
                                f"references id {token!r}, which was not found "
                                f"anywhere in the document"
                            ),
                        )
                    )
    return tuple(diagnostics)


def find_duplicate_ids(
    root: ParsedElement,
    *,
    id_attribute_names: tuple[str, ...] = _DEFAULT_ID_ATTRIBUTE_NAMES,
) -> tuple[ParseDiagnostic, ...]:
    """Find id values that are carried by more than one element.

    :func:`~meca_engine.extraction.navigation.build_id_index` silently
    keeps only the first element for a repeated id value (by design, for
    a stable single-answer lookup) — this function is the companion
    check its own docstring points callers at for detecting that a
    repeat happened at all.

    Args:
        root: The subtree to scan.
        id_attribute_names: Forwarded to
            :func:`~meca_engine.extraction.navigation.build_id_index`.

    Returns:
        One WARNING-severity, ``DUPLICATE_ID``-category diagnostic per
        element beyond the first that repeats an already-seen id value,
        in document order.
    """
    seen: set[str] = set()
    diagnostics: list[ParseDiagnostic] = []
    for element in iter_descendants(root):
        for attribute in element.attributes:
            is_plain_id = attribute.namespace_uri is None and attribute.name in id_attribute_names
            is_xml_id = attribute.namespace_uri == XML_NAMESPACE_URI and attribute.name == "id"
            if not (is_plain_id or is_xml_id):
                continue
            if attribute.value in seen:
                diagnostics.append(
                    ParseDiagnostic(
                        severity=DiagnosticSeverity.WARNING,
                        category=DiagnosticCategory.DUPLICATE_ID,
                        message=(
                            f"Element <{element.tag}> repeats id {attribute.value!r}, "
                            f"already used elsewhere in the document"
                        ),
                    )
                )
            else:
                seen.add(attribute.value)
    return tuple(diagnostics)


def find_malformed_references(
    root: ParsedElement,
    *,
    reference_attribute_names: tuple[str, ...] = _DEFAULT_REFERENCE_ATTRIBUTE_NAMES,
) -> tuple[ParseDiagnostic, ...]:
    """Find reference attributes present but carrying no usable id token.

    Distinct from :func:`find_dangling_references` (which checks whether
    a reference's *target* exists): this checks whether the reference
    attribute itself is structurally empty (``rid=""`` or whitespace
    only) — a source-fidelity observation, not a target-lookup one.

    Args:
        root: The subtree to scan.
        reference_attribute_names: Which unprefixed attribute names count
            as holding a reference. Defaults to ``("rid",)``.

    Returns:
        One WARNING-severity, ``MISSING_REQUIRED_VALUE``-category
        diagnostic per empty reference attribute found, in document
        order.
    """
    diagnostics: list[ParseDiagnostic] = []
    for element in iter_descendants(root):
        for attribute in element.attributes:
            if (
                attribute.namespace_uri is not None
                or attribute.name not in reference_attribute_names
            ):
                continue
            if not attribute.value.split():
                diagnostics.append(
                    ParseDiagnostic(
                        severity=DiagnosticSeverity.WARNING,
                        category=DiagnosticCategory.MISSING_REQUIRED_VALUE,
                        message=(
                            f"Element <{element.tag}> attribute {attribute.name!r} "
                            f"is present but carries no reference value"
                        ),
                    )
                )
    return tuple(diagnostics)
