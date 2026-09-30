"""Manifest XML Generator — produces <ArticleID>_manifest.xml (Business Rule Book §F, BR-076–095).

Implemented in Milestone 6D, reusing the Generator Framework (Milestone
6A) exactly as raw.xml (6B) and article.xml (6C) do — no manual
ElementTree construction outside :class:`~meca_engine.generators.xml.builder.XmlDocumentBuilder`,
no duplicated helper logic.

Per 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.7: "3 fixed items + one
item per `ResolvedFile`, item-type via `item_type_mapper`, ordering per
BR-083, clean id/description generation (ADR-010/011)." Unlike
article.xml, this generator depends on **no other generator** — only the
ICAM (``model.identity``, ``model.resolved_files``, ``model.rounds``)
and configuration (``ItemTypeMappingConfig``, ``MediaTypeConfig``,
``ManifestXmlConfig``, ``NamespaceManager``).

**Evidence-over-documentation corrections** (see the Manifest Decision
Log for full detail):

- BR-084/BR-085 each confirm the 3 real reference packages' own observed
  item-description/item-id patterns are clerical defects, not rules —
  ADR-010/011 each recommend a clean replacement, implemented here
  (``ManifestXmlConfig.file_item_description_template``/``file_item_id_prefix``).
- A file item's ``instance/@xlink:href`` filename component is the
  *physically resolved* file's own name
  (``Path(resolved_file.staged_physical_path).name``), not
  ``resolved_file.original_filename`` — confirmed against real evidence
  (e.g. CS-2025-6808's declared name ``"Table 2"`` resolves to the
  physical file ``"Table 2 (1).docx"``, and the real manifest.xml's href
  uses the latter) even though BR-013's text claims the declared name is
  used byte-identical; trusted here as the same kind of
  evidence-over-documentation correction already established in
  Milestone 6C (BR-070).
"""

from __future__ import annotations

from pathlib import PurePath
from typing import TYPE_CHECKING

from meca_engine.exceptions import GeneratorInvariantError
from meca_engine.generators.base import BaseGenerator
from meca_engine.generators.manifest_xml.document import ManifestXmlDocument
from meca_engine.generators.xml.builder import DoctypeDeclaration, XmlDocumentBuilder
from meca_engine.generators.xml.helpers import add_optional_element
from meca_engine.utils.media_types import resolve_media_type

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from meca_engine.config.schema import (
        ItemTypeMappingConfig,
        ManifestXmlConfig,
        MediaTypeConfig,
    )
    from meca_engine.generators.context import GeneratorContext
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.xml.namespaces import NamespaceManager
    from meca_engine.model.article import ArticleIdentity, ResolvedFile
    from meca_engine.model.collections import ResolvedFileList, RoundIndex

_GENERATOR_NAME = "manifest_xml"
_MANIFEST_NAMESPACE_PREFIX = "meca-manifest"
_XLINK_NAMESPACE_PREFIX = "xlink"
_XML_EXTENSION = ".xml"
_UNKNOWN_ROUND_SORT_KEY = -1


class ManifestXmlGenerator(BaseGenerator[ManifestXmlDocument]):
    """Generates manifest.xml from the ICAM. See module docstring for BR traceability."""

    def __init__(
        self,
        *,
        namespace_manager: NamespaceManager,
        manifest_xml_config: ManifestXmlConfig,
        item_type_mapping: ItemTypeMappingConfig,
        media_type_config: MediaTypeConfig,
    ) -> None:
        """Initialize the generator.

        Args:
            namespace_manager: Resolves BR-076's default/`xlink` namespaces.
            manifest_xml_config: BR-076/086/087/095's externalized
                constants and ADR-010/011's clean id/description templates.
            item_type_mapping: BR-078's category → item-type lookup.
            media_type_config: BR-081's extension → MIME-type lookup.
        """
        self._namespace_manager = namespace_manager
        self._config = manifest_xml_config
        self._item_type_mapping = item_type_mapping
        self._media_type_config = media_type_config

    @property
    def generator_name(self) -> str:
        """This generator's stable name, ``"manifest_xml"``."""
        return _GENERATOR_NAME

    def _generate(self, context: GeneratorContext) -> ManifestXmlDocument:
        model = context.model
        config = self._config
        diagnostics = context.diagnostics

        builder = XmlDocumentBuilder()
        root = builder.create_root(
            "manifest",
            attributes={
                "xmlns": self._require_uri(_MANIFEST_NAMESPACE_PREFIX),
                "xmlns:xlink": self._require_uri(_XLINK_NAMESPACE_PREFIX),
                "manifest-version": config.manifest_version,  # BR-087
            },
        )

        _add_fixed_items(
            builder, root, model.identity, config, self._media_type_config, diagnostics
        )
        _add_file_items(
            builder,
            root,
            model.resolved_files,
            model.rounds,
            config,
            self._item_type_mapping,
            self._media_type_config,
            diagnostics,
        )

        xml_bytes = builder.serialize(
            root,
            pretty=True,
            encoding=config.encoding,  # BR-086
            indent_spaces=config.pretty_indent_spaces,
            doctype=DoctypeDeclaration(  # BR-076/095
                root_tag="manifest",
                public_id=config.doctype_public_id,
                system_id=config.doctype_system_id,
            ),
        )

        return ManifestXmlDocument(
            article_id=model.identity.article_id,
            filename=f"{model.identity.article_id}_manifest.xml",  # BR-088
            xml_bytes=xml_bytes,
        )

    def _require_uri(self, prefix: str) -> str:
        uri = self._namespace_manager.uri_for(prefix)
        if uri is None:
            raise GeneratorInvariantError(
                f"Namespace prefix {prefix!r} is not registered in the namespace configuration",
                stage=_GENERATOR_NAME,
            )
        return uri


# --- 3 fixed items (BR-077/079/080/092) ---------------------------------------


def _add_fixed_items(
    builder: XmlDocumentBuilder,
    root: Element,
    identity: ArticleIdentity,
    config: ManifestXmlConfig,
    media_type_config: MediaTypeConfig,
    diagnostics: DiagnosticsCollector,
) -> None:
    xml_media_type, _ = resolve_media_type(f"placeholder{_XML_EXTENSION}", media_type_config)

    if not identity.publisher_id_value:
        diagnostics.warn(
            _GENERATOR_NAME,
            "No publisher-id available for the item-article description (BR-080)",
        )
    _add_item(
        builder,
        root,
        item_id="item-article",
        item_type="article-metadata",
        description=config.item_article_description_template.format(
            publisher_id=identity.publisher_id_value
        ),
        media_type=xml_media_type,
        href=config.article_filename_pattern.format(article_id=identity.article_id),
    )
    _add_item(
        builder,
        root,
        item_id="item-reviews",
        item_type="review-metadata",
        description=config.item_reviews_description,
        media_type=xml_media_type,
        href=config.reviews_filename_pattern.format(article_id=identity.article_id),
    )
    _add_item(
        builder,
        root,
        item_id="item-transfer",
        item_type="transfer-metadata",
        description=config.item_transfer_description,
        media_type=xml_media_type,
        href=config.transfer_filename_pattern.format(article_id=identity.article_id),
    )


# --- file items (BR-078/081-085/093/094) --------------------------------------


def _add_file_items(
    builder: XmlDocumentBuilder,
    root: Element,
    resolved_files: ResolvedFileList,
    rounds: RoundIndex,
    config: ManifestXmlConfig,
    item_type_mapping: ItemTypeMappingConfig,
    media_type_config: MediaTypeConfig,
    diagnostics: DiagnosticsCollector,
) -> None:
    if not resolved_files:
        diagnostics.info(_GENERATOR_NAME, "No resolved files available to list in manifest.xml")
        return

    _diagnose_duplicate_checksums(resolved_files, diagnostics)

    round_sort_key = {round_info.label: round_info.sequence_number for round_info in rounds}
    ordered_files = sorted(  # BR-083: latest round first, stable within each round
        resolved_files,
        key=lambda f: -round_sort_key.get(f.round_label, _UNKNOWN_ROUND_SORT_KEY),
    )

    for sequence, resolved_file in enumerate(ordered_files, start=1):
        if resolved_file.round_label not in round_sort_key:
            diagnostics.warn(
                _GENERATOR_NAME,
                f"File {resolved_file.original_filename!r} references round label "
                f"{resolved_file.round_label!r}, which is not in the round index",
            )
        item_type = item_type_mapping.mappings.get(  # BR-078
            resolved_file.category, item_type_mapping.default_item_type
        )
        physical_filename = PurePath(resolved_file.staged_physical_path).name
        media_type, matched = resolve_media_type(physical_filename, media_type_config)  # BR-081
        if not matched:
            diagnostics.warn(
                _GENERATOR_NAME,
                f"Unresolved media type for {physical_filename!r}; "
                f"defaulted to {media_type!r} (ADR-009)",
            )
        _add_item(
            builder,
            root,
            item_id=f"{config.file_item_id_prefix}{sequence}",  # BR-085
            item_type=item_type,
            description=config.file_item_description_template.format(  # BR-084
                category=resolved_file.category,
                original_filename=resolved_file.original_filename,
                size_bytes=resolved_file.size_bytes,
            ),
            media_type=media_type,
            href=f"files/{resolved_file.round_label}/{physical_filename}",  # BR-082
        )


def _diagnose_duplicate_checksums(
    resolved_files: ResolvedFileList, diagnostics: DiagnosticsCollector
) -> None:
    seen: dict[str, ResolvedFile] = {}
    for resolved_file in resolved_files:
        earlier = seen.get(resolved_file.checksum)
        if earlier is not None:
            diagnostics.info(
                _GENERATOR_NAME,
                f"{resolved_file.original_filename!r} has identical content to "
                f"{earlier.original_filename!r} (same checksum) — both are still listed",
            )
        else:
            seen[resolved_file.checksum] = resolved_file


# --- shared <item> shape -------------------------------------------------------


def _add_item(
    builder: XmlDocumentBuilder,
    root: Element,
    *,
    item_id: str,
    item_type: str,
    description: str,
    media_type: str,
    href: str,
) -> None:
    item = builder.create_element(root, "item", attributes={"id": item_id, "item-type": item_type})
    add_optional_element(builder, item, "item-description", description)
    builder.create_element(
        item, "instance", attributes={"media-type": media_type, "xlink:href": href}
    )
