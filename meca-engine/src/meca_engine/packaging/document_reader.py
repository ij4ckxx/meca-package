"""Reads facts back out of already-generated XML documents — Milestone 7.

Package Assembly must treat manifest.xml as the authoritative list of
packaged files ("never scan directories to decide package contents";
Milestone 7 task instructions) and must not recompute the DOI itself
("no business logic inside Package Builder"). Both facts already exist,
fully decided, inside bytes the generators already produced — this
module's only job is to read them back out, exactly as
:mod:`meca_engine.generators.xml.helpers` already does for every
generator that needs to re-parse an already-serialized fragment. No
value here is derived, inferred, or defaulted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.exceptions.article_errors import GeneratorInvariantError
from meca_engine.generators.xml.helpers import parse_document_with_namespaces

if TYPE_CHECKING:
    from meca_engine.generators.xml.namespaces import NamespaceManager

_STAGE = "meca_engine.packaging.document_reader"
_MANIFEST_NAMESPACE_PREFIX = "meca-manifest"
_XLINK_NAMESPACE_PREFIX = "xlink"
_FILE_HREF_PREFIX = "files/"


def extract_packaged_file_hrefs(
    manifest_xml_bytes: bytes, namespace_manager: NamespaceManager
) -> tuple[str, ...]:
    """Return every physical-asset href manifest.xml declares, in document order.

    Excludes the 3 fixed metadata items (article/reviews/transfer
    self-references, BR-077/079/080) — their hrefs never start with
    ``"files/"`` (BR-082's own, already-established convention), unlike
    every genuine per-``ResolvedFile`` item.

    Args:
        manifest_xml_bytes: The bytes manifest.xml's own
            :class:`~meca_engine.generators.manifest_xml.generator.ManifestXmlGenerator`
            produced.
        namespace_manager: Resolves the ``meca-manifest``/``xlink``
            namespace URIs this document was serialized with.

    Returns:
        Every ``files/...`` href, in the exact order manifest.xml itself
        lists them — this order is authoritative and must never be
        re-sorted by this or any downstream Package Assembly component
        (see 34_TECHNICAL_DEBT_REGISTER.md TD-1).

    Raises:
        GeneratorInvariantError: If the ``meca-manifest`` or ``xlink``
            namespace is not registered — a configuration defect, not a
            data-quality issue.
    """
    manifest_uri = namespace_manager.uri_for(_MANIFEST_NAMESPACE_PREFIX)
    xlink_uri = namespace_manager.uri_for(_XLINK_NAMESPACE_PREFIX)
    if manifest_uri is None or xlink_uri is None:
        raise GeneratorInvariantError(
            "Required namespace not registered for manifest.xml parsing "
            f"(meca-manifest={manifest_uri!r}, xlink={xlink_uri!r})",
            stage=_STAGE,
        )
    root = parse_document_with_namespaces(
        manifest_xml_bytes, {"xmlns": manifest_uri, "xmlns:xlink": xlink_uri}
    )
    hrefs: list[str] = []
    for item in root.findall("item"):
        instance = item.find("instance")
        if instance is None:
            continue
        href = instance.get("xlink:href")
        if href is not None and href.startswith(_FILE_HREF_PREFIX):
            hrefs.append(href)
    return tuple(hrefs)


def extract_generated_doi(article_xml_bytes: bytes) -> str | None:
    """Return the generated DOI already embedded in article.xml, or ``None``.

    Reads ``article-meta/article-id[@pub-id-type="doi"]`` — the value
    :mod:`meca_engine.generators.article_xml.generator` already computed
    per BR-058/059. This function never derives, prefixes, or normalizes
    a DOI itself.

    Args:
        article_xml_bytes: The bytes article.xml's own
            :class:`~meca_engine.generators.article_xml.generator.ArticleXmlGenerator`
            produced.

    Returns:
        The DOI text, or ``None`` if no ``doi``-typed ``article-id``
        element is present (e.g. ``MissingDoiError`` was diagnosed rather
        than raised upstream in a non-strict configuration).
    """
    root = parse_document_with_namespaces(article_xml_bytes, {})
    for article_id_element in root.findall(".//article-id"):
        if article_id_element.get("pub-id-type") == "doi":
            return article_id_element.text
    return None
