"""XSLT-based raw.xml transform — Milestone 9.

Applies `rawtocleanup.xslt` (packaged alongside this module) to the
original source XML, producing raw.xml's JATS Publishing DTD v1.3
content directly from real source markup — a structural cleanup
transform, not a field-by-field ICAM mapping. This is why
:class:`~meca_engine.generators.raw_xml.xslt_generator.XsltRawXmlGenerator`
is the one documented exception to "the ICAM is the only route to
article data" (see `generators/base.py`'s module docstring).

**XXE hardening**: mirrors this project's existing `defusedxml`
rationale (`pyproject.toml`) — every parser constructed here disables
network access and external entity resolution, both for the stylesheet
and for the source XML being transformed. Never rely on lxml's
permissive defaults.

**Correction (Milestone 9, applied to the packaged stylesheet, not this
module)**: the original `rawtocleanup.xslt` pruned `custom-meta-group`
entries by `specific-use`/`meta-name`/emptiness. Verified against all 3
real reference packages (`Output/MECA_*.zip`), the actual rule is more
selective than either "prune these categories" or "prune nothing":

- `specific-use="query"/"reviewer-decline"/"question"`, `data-type=
  "email-draft"`, and specific named `meta-name` keys (proofingEngine,
  payment received, etc.): real references retain these 100% — the
  original pruning templates for them have been removed.
- `specific-use="track-changes"`: real reference (`CS-2025-6808`, the
  only sample with any) drops these 100% (22/22) — this one pruning
  template has been kept/restored.
- `specific-use="history"`: **genuinely contradictory evidence across
  samples, deliberately left unresolved.** `CS-2025-8493_C` retains
  100% (70/70) including `xlink:role="preeditor"/"copyeditor"/
  "typesetter"` entries; `CS-2025-6808` retains only 18/142, and no
  role-based, title-based, or dedup-based rule found so far explains
  both samples simultaneously (a role-based hypothesis and an
  xlink:title-dedup hypothesis were each confirmed by one sample and
  falsified by the other). Left unpruned (matching 2 of 3 samples
  exactly) rather than guess at a rule not supported by the evidence —
  needs more real samples or business input before attempting again.

Two further gaps were found but deliberately deferred (not yet fixed,
tracked separately): (1) a `data-*` attribute whitelist that drops
attributes the real reference retains (e.g. `data-version`,
`data-reviewer-name`), and (2) `named-content` children inside
`custom-meta/meta-value` still being dropped by content-type-based
removal templates elsewhere in the stylesheet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from lxml import etree

from meca_engine.exceptions import SourceXmlMalformedError, XmlSerializationError

_XSLT_PATH: Final[Path] = Path(__file__).parent / "rawtocleanup.xslt"
_STAGE: Final[str] = "generators.raw_xml.xslt_transform"


def _hardened_parser() -> etree.XMLParser:
    """An XML parser with external entity resolution and network access disabled."""
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        dtd_validation=False,
        huge_tree=False,
    )


def _load_transform() -> etree.XSLT:
    parser = _hardened_parser()
    stylesheet_doc = etree.parse(str(_XSLT_PATH), parser)
    return etree.XSLT(stylesheet_doc)


_TRANSFORM: Final[etree.XSLT] = _load_transform()


def transform(source_xml_bytes: bytes, *, article_id: str | None = None) -> bytes:
    """Apply `rawtocleanup.xslt` to source XML, returning raw.xml's bytes.

    Args:
        source_xml_bytes: The original source XML, verbatim.
        article_id: The article this source belongs to, for error
            context only (never used to alter the transform itself).

    Returns:
        The transformed document, serialized as UTF-8 bytes, including
        the DOCTYPE declaration the stylesheet's ``<xsl:output>``
        specifies.

    Raises:
        SourceXmlMalformedError: If ``source_xml_bytes`` is not
            well-formed XML.
        XmlSerializationError: If the XSLT transform itself fails.
    """
    parser = _hardened_parser()
    try:
        source_doc = etree.fromstring(source_xml_bytes, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise SourceXmlMalformedError(
            f"Source XML is not well-formed: {exc}",
            article_id=article_id,
            stage=_STAGE,
            inner_cause=exc,
        ) from exc

    try:
        result = _TRANSFORM(source_doc)
    except etree.XSLTApplyError as exc:
        raise XmlSerializationError(
            f"XSLT transform failed: {exc}",
            article_id=article_id,
            stage=_STAGE,
            inner_cause=exc,
        ) from exc

    return bytes(result)
