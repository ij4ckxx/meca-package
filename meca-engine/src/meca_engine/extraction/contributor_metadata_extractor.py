"""Contributor-level metadata extraction — Milestone 4.

Reads author/editor/other-contributor and affiliation values (including
name suffix and equal-contribution status) out of a
:class:`~meca_engine.extraction.parsed_model.ParsedDocument`. A pure
function: no logging, no I/O, no exceptions for missing fields. Returns
no diagnostics (an empty tuple) — no source value here is clear-cut
enough to call "required" without guessing — but keeps the same
``tuple[Model, tuple[ParseDiagnostic, ...]]`` return shape as every other
extractor, so :mod:`meca_engine.extraction.metadata_extraction` can treat
all seven uniformly. Sorting into authors/editors/others relies only on
the source's own ``contrib-type`` value — never reclassified.

**Correction**: affiliation fields are read from Kriyadocs's own
``<named-content content-type="...">`` tagging (institution/department/
city/state/country), not JATS's literal ``<institution>``/``<country>``
elements — the source never uses the latter, so the original lookup
always missed and fell back to dumping the whole affiliation's raw text
into one field. ``_EDITOR_TYPES`` also now includes ``"associate-editor"``
(previously only ``"editor"`` matched, silently routing associate editors
into ``other_contributors``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.extraction.metadata_models import (
    AffiliationRecord,
    ContributorMetadata,
    ContributorRecord,
)
from meca_engine.extraction.navigation import find_all, find_first, get_attribute, get_text

if TYPE_CHECKING:
    from meca_engine.extraction.parsed_model import ParsedDocument, ParsedElement, ParseDiagnostic

_AUTHOR_TYPES = frozenset({"author"})
_EDITOR_TYPES = frozenset({"editor", "associate-editor"})

# Kriyadocs tags affiliation fields as `<named-content content-type="...">`
# rather than JATS's own `<institution>`/`<country>` elements. Observed
# content-type spellings across all known source packages (Milestone 9
# affiliation-structure correction) — "dept" and "department" are both
# seen and treated as the same field.
_DEPARTMENT_CONTENT_TYPES = frozenset({"department", "dept"})
_INSTITUTION_CONTENT_TYPES = frozenset({"institution"})
_CITY_CONTENT_TYPES = frozenset({"city"})
_STATE_CONTENT_TYPES = frozenset({"state"})
_COUNTRY_CONTENT_TYPES = frozenset({"country"})


def _named_content_text(element: ParsedElement, content_types: frozenset[str]) -> str | None:
    for named_content in find_all(element, "named-content", recursive=False):
        if get_attribute(named_content, "content-type") in content_types:
            return get_text(named_content, recursive=True)
    return None


def _extract_affiliation(element: ParsedElement) -> AffiliationRecord:
    label_element = find_first(element, "label", recursive=False)
    return AffiliationRecord(
        element_id=get_attribute(element, "id"),
        label=get_text(label_element, recursive=True) if label_element is not None else None,
        department=_named_content_text(element, _DEPARTMENT_CONTENT_TYPES),
        institution=_named_content_text(element, _INSTITUTION_CONTENT_TYPES),
        city=_named_content_text(element, _CITY_CONTENT_TYPES),
        state=_named_content_text(element, _STATE_CONTENT_TYPES),
        country=_named_content_text(element, _COUNTRY_CONTENT_TYPES),
        raw_text=get_text(element, recursive=True),
    )


def _is_corresponding(element: ParsedElement) -> bool:
    if get_attribute(element, "corresp") == "yes":
        return True
    return any(get_attribute(xref, "ref-type") == "corresp" for xref in find_all(element, "xref"))


def _extract_affiliation_ref_ids(element: ParsedElement) -> tuple[str, ...]:
    ref_ids: list[str] = []
    for xref in find_all(element, "xref"):
        if get_attribute(xref, "ref-type") != "aff":
            continue
        rid = get_attribute(xref, "rid")
        if rid is not None:
            ref_ids.append(rid)
    return tuple(ref_ids)


def _extract_contributor(element: ParsedElement) -> ContributorRecord:
    name_element = find_first(element, "name")
    surname_element = find_first(name_element, "surname") if name_element is not None else None
    given_names_element = (
        find_first(name_element, "given-names") if name_element is not None else None
    )
    suffix_element = find_first(name_element, "suffix") if name_element is not None else None
    orcid_element = find_first(element, "contrib-id")
    return ContributorRecord(
        contrib_type=get_attribute(element, "contrib-type"),
        surname=(
            get_text(surname_element, recursive=True) if surname_element is not None else None
        ),
        given_names=(
            get_text(given_names_element, recursive=True)
            if given_names_element is not None
            else None
        ),
        orcid=get_text(orcid_element, recursive=True) if orcid_element is not None else None,
        emails=tuple(get_text(email, recursive=True) for email in find_all(element, "email")),
        affiliation_ref_ids=_extract_affiliation_ref_ids(element),
        is_corresponding=_is_corresponding(element),
        suffix=get_text(suffix_element, recursive=True) if suffix_element is not None else None,
        equal_contrib=get_attribute(element, "equal-contrib") == "yes",
        is_submitting_author=get_attribute(element, "data-submitting-author") == "yes",
    )


def extract_contributor_metadata(
    document: ParsedDocument,
) -> tuple[ContributorMetadata, tuple[ParseDiagnostic, ...]]:
    """Extract contributor-level metadata from a parsed document.

    Args:
        document: The parsed document to read from.

    Returns:
        The extracted
        :class:`~meca_engine.extraction.metadata_models.ContributorMetadata`,
        alongside an always-empty diagnostics tuple. Contributors are
        sorted into authors/editors/other-contributors by their source
        ``contrib-type`` value only.
    """
    article_meta = find_first(document.root, "article-meta")
    if article_meta is None:
        return ContributorMetadata(), ()

    authors: list[ContributorRecord] = []
    editors: list[ContributorRecord] = []
    others: list[ContributorRecord] = []
    for element in find_all(article_meta, "contrib"):
        record = _extract_contributor(element)
        if record.contrib_type in _AUTHOR_TYPES:
            authors.append(record)
        elif record.contrib_type in _EDITOR_TYPES:
            editors.append(record)
        else:
            others.append(record)

    affiliations = tuple(_extract_affiliation(element) for element in find_all(article_meta, "aff"))

    metadata = ContributorMetadata(
        authors=tuple(authors),
        editors=tuple(editors),
        other_contributors=tuple(others),
        affiliations=affiliations,
    )
    return metadata, ()
