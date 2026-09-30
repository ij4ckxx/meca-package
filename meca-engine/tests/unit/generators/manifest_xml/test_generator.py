"""Unit tests for meca_engine.generators.manifest_xml.generator.ManifestXmlGenerator."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from xml.etree.ElementTree import fromstring

import pytest

from meca_engine.exceptions import GeneratorInvariantError
from meca_engine.generators.manifest_xml.generator import ManifestXmlGenerator
from meca_engine.generators.result import GenerationResult
from meca_engine.generators.xml.namespaces import NamespaceManager
from meca_engine.model.article import RoundInfo

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from meca_engine.config.schema import (
        ItemTypeMappingConfig,
        ManifestXmlConfig,
        MediaTypeConfig,
    )
    from meca_engine.generators.context import GeneratorContext
    from meca_engine.generators.manifest_xml.document import ManifestXmlDocument

pytestmark = pytest.mark.unit

_NS = {
    "m": "https://manuscriptexchange.org/schema/manifest",
    "xlink": "http://www.w3.org/1999/xlink",
}


def _decode(document: ManifestXmlDocument) -> str:
    return document.xml_bytes.decode("utf-8")


def _items(document: ManifestXmlDocument) -> list[Element]:
    root = fromstring(document.xml_bytes)
    return root.findall("m:item", _NS)


def _href(item: Element) -> str | None:
    instance = item.find("m:instance", _NS)
    return instance.get("{http://www.w3.org/1999/xlink}href") if instance is not None else None


# --- lifecycle / framework usage ----------------------------------------------


def test_generator_name_is_manifest_xml(manifest_xml_generator: ManifestXmlGenerator) -> None:
    assert manifest_xml_generator.generator_name == "manifest_xml"


def test_generate_returns_a_generation_result(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = manifest_xml_generator.generate(rich_context)

    assert isinstance(result, GenerationResult)
    assert result.article_id == "cs-2025-0001"
    assert result.generator_name == "manifest_xml"
    assert result.duration_ms >= 0


def test_filename_matches_br_088_pattern(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = manifest_xml_generator.generate(rich_context)

    assert result.document.filename == "cs-2025-0001_manifest.xml"


def test_output_is_well_formed_xml(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = manifest_xml_generator.generate(rich_context)

    fromstring(result.document.xml_bytes)  # raises if not well-formed


# --- root / DOCTYPE / namespaces (BR-076/086/087/095) --------------------------


def test_xml_declaration_matches_br_086(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(manifest_xml_generator.generate(rich_context).document)

    assert output.startswith('<?xml version="1.0" encoding="UTF-8"?>')


def test_doctype_matches_br_076_and_br_095(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(manifest_xml_generator.generate(rich_context).document)

    assert (
        '<!DOCTYPE manifest PUBLIC "-//MECA//DTD Manifest v1.0//en" "./schema/manifest-1.0.dtd">'
        in output
    )


def test_root_declares_default_and_xlink_namespaces_br_076(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(manifest_xml_generator.generate(rich_context).document.xml_bytes)

    assert root.tag == "{https://manuscriptexchange.org/schema/manifest}manifest"


def test_manifest_version_matches_br_087(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(manifest_xml_generator.generate(rich_context).document.xml_bytes)

    assert root.get("manifest-version") == "1"


def test_unregistered_default_namespace_raises_generator_invariant_error(
    manifest_xml_config: ManifestXmlConfig,
    item_type_mapping: ItemTypeMappingConfig,
    media_type_config: MediaTypeConfig,
    rich_context: GeneratorContext,
) -> None:
    namespace_manager_without_manifest_ns = NamespaceManager(
        {"xlink": "http://www.w3.org/1999/xlink"}
    )
    generator = ManifestXmlGenerator(
        namespace_manager=namespace_manager_without_manifest_ns,
        manifest_xml_config=manifest_xml_config,
        item_type_mapping=item_type_mapping,
        media_type_config=media_type_config,
    )

    with pytest.raises(GeneratorInvariantError):
        generator.generate(rich_context)


def test_unregistered_xlink_namespace_raises_generator_invariant_error(
    manifest_xml_config: ManifestXmlConfig,
    item_type_mapping: ItemTypeMappingConfig,
    media_type_config: MediaTypeConfig,
    rich_context: GeneratorContext,
) -> None:
    namespace_manager_without_xlink = NamespaceManager(
        {"meca-manifest": "https://manuscriptexchange.org/schema/manifest"}
    )
    generator = ManifestXmlGenerator(
        namespace_manager=namespace_manager_without_xlink,
        manifest_xml_config=manifest_xml_config,
        item_type_mapping=item_type_mapping,
        media_type_config=media_type_config,
    )

    with pytest.raises(GeneratorInvariantError):
        generator.generate(rich_context)


# --- pretty-printing (evidence: 2-space hierarchical indent) -------------------


def test_output_uses_two_space_hierarchical_indentation(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(manifest_xml_generator.generate(rich_context).document)

    assert '\n  <item id="item-article"' in output
    assert "\n    <item-description>" in output


# --- 3 fixed items (BR-077/079/080/092) -----------------------------------------


def test_exactly_three_fixed_items_appear_first_br_077(
    manifest_xml_generator: ManifestXmlGenerator, empty_context: GeneratorContext
) -> None:
    items = _items(manifest_xml_generator.generate(empty_context).document)

    assert [item.get("id") for item in items[:3]] == [
        "item-article",
        "item-reviews",
        "item-transfer",
    ]
    assert [item.get("item-type") for item in items[:3]] == [
        "article-metadata",
        "review-metadata",
        "transfer-metadata",
    ]


def test_fixed_items_present_even_for_the_simplest_package_br_092(
    manifest_xml_generator: ManifestXmlGenerator, empty_context: GeneratorContext
) -> None:
    items = _items(manifest_xml_generator.generate(empty_context).document)

    assert len(items) == 3


def test_item_article_description_interpolates_publisher_id_br_079_080(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    items = _items(manifest_xml_generator.generate(rich_context).document)

    description = items[0].findtext("m:item-description", namespaces=_NS)
    assert description == "Article metadata exported from JATS (publisher-id: EX-2025-001)"


def test_item_reviews_and_transfer_descriptions_are_constant_br_079(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    items = _items(manifest_xml_generator.generate(rich_context).document)

    assert (
        items[1].findtext("m:item-description", namespaces=_NS)
        == "MECA reviews.xml generated from JATS custom-meta and history dates"
    )
    assert (
        items[2].findtext("m:item-description", namespaces=_NS)
        == "MECA transfer.xml with source/destination info"
    )


def test_fixed_item_hrefs_use_the_configured_filename_patterns(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    items = _items(manifest_xml_generator.generate(rich_context).document)

    assert _href(items[0]) == "cs-2025-0001_article.xml"
    assert _href(items[1]) == "cs-2025-0001_reviews.xml"
    assert _href(items[2]) == "cs-2025-0001_transfer.xml"


def test_fixed_items_use_application_xml_media_type_br_081(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    items = _items(manifest_xml_generator.generate(rich_context).document)

    for item in items[:3]:
        instance = item.find("m:instance", _NS)
        assert instance is not None
        assert instance.get("media-type") == "application/xml"


def test_missing_publisher_id_is_diagnosed_but_still_produces_a_document(
    manifest_xml_generator: ManifestXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = manifest_xml_generator.generate(empty_context)

    assert any("publisher-id" in d.message for d in result.diagnostics)
    items = _items(result.document)
    assert items[0].findtext("m:item-description", namespaces=_NS) == (
        "Article metadata exported from JATS (publisher-id: )"
    )


# --- file items: inventory, ordering, ids, media types (BR-078/081-085/093/094) --


def test_no_resolved_files_is_diagnosed_and_contributes_zero_file_items_br_093(
    manifest_xml_generator: ManifestXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = manifest_xml_generator.generate(empty_context)

    assert any("No resolved files" in d.message for d in result.diagnostics)
    assert len(_items(result.document)) == 3


def test_item_count_equals_three_plus_file_count_br_094(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = manifest_xml_generator.generate(rich_context)

    assert len(_items(result.document)) == 3 + len(rich_context.model.resolved_files)


def test_latest_round_files_listed_before_earlier_round_files_br_083(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    items = _items(manifest_xml_generator.generate(rich_context).document)
    file_items = items[3:]

    hrefs = [_href(item) for item in file_items]
    assert hrefs == [
        "files/R1/manuscript.docx",
        "files/R1/fig1.jpg",
        "files/Original/manuscript.docx",
    ]


def test_within_a_round_file_order_is_preserved(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    items = _items(manifest_xml_generator.generate(rich_context).document)
    r1_hrefs = [_href(item) for item in items[3:] if "files/R1/" in (_href(item) or "")]

    assert r1_hrefs == ["files/R1/manuscript.docx", "files/R1/fig1.jpg"]


def test_file_item_ids_are_flat_sequential_br_085(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    items = _items(manifest_xml_generator.generate(rich_context).document)
    file_item_ids = [item.get("id") for item in items[3:]]

    assert file_item_ids == ["file-1", "file-2", "file-3"]


def test_file_item_description_uses_the_clean_template_br_084(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    items = _items(manifest_xml_generator.generate(rich_context).document)

    description = items[3].findtext("m:item-description", namespaces=_NS)
    assert description == "manuscript — manuscript (1024 bytes)"


def test_item_type_uses_the_configured_mapping_br_078(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    items = _items(manifest_xml_generator.generate(rich_context).document)

    assert items[3].get("item-type") == "manuscript"
    assert items[4].get("item-type") == "figure"


def test_unmapped_category_falls_back_to_default_item_type_br_078(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    unmapped_file = replace(rich_context.model.resolved_files[0], category="responsetoreviewer")
    context = replace(
        rich_context, model=replace(rich_context.model, resolved_files=(unmapped_file,))
    )

    items = _items(manifest_xml_generator.generate(context).document)

    assert items[3].get("item-type") == "supplemental"


def test_href_uses_the_physical_filename_not_the_declared_name(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    disambiguated_file = replace(
        rich_context.model.resolved_files[0],
        original_filename="Table 2",
        staged_physical_path="/staged/R1/Table 2 (1).docx",
    )
    context = replace(
        rich_context, model=replace(rich_context.model, resolved_files=(disambiguated_file,))
    )

    items = _items(manifest_xml_generator.generate(context).document)

    assert _href(items[3]) == "files/R1/Table 2 (1).docx"


def test_href_is_not_percent_encoded_br_090(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    spaced_file = replace(
        rich_context.model.resolved_files[0],
        staged_physical_path="/staged/R1/Figure 1 (final).jpg",
    )
    context = replace(
        rich_context, model=replace(rich_context.model, resolved_files=(spaced_file,))
    )

    output = _decode(manifest_xml_generator.generate(context).document)

    assert "files/R1/Figure 1 (final).jpg" in output
    assert "%20" not in output


# --- media type resolution / diagnostics ----------------------------------------


def test_resolved_extension_uses_the_configured_media_type(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    items = _items(manifest_xml_generator.generate(rich_context).document)

    instance = items[3].find("m:instance", _NS)
    assert instance is not None
    assert instance.get("media-type") == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_unmapped_extension_defaults_and_is_diagnosed(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    unmapped_file = replace(
        rich_context.model.resolved_files[0], staged_physical_path="/staged/R1/data.unknownext"
    )
    context = replace(
        rich_context, model=replace(rich_context.model, resolved_files=(unmapped_file,))
    )

    result = manifest_xml_generator.generate(context)
    items = _items(result.document)

    instance = items[3].find("m:instance", _NS)
    assert instance is not None
    assert instance.get("media-type") == "application/octet-stream"
    assert any("Unresolved media type" in d.message for d in result.diagnostics)


# --- duplicate handling ----------------------------------------------------------


def test_duplicate_checksum_is_diagnosed_but_both_items_still_listed(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    original = rich_context.model.resolved_files[0]
    duplicate = replace(original, original_filename="a-second-copy")
    context = replace(
        rich_context,
        model=replace(rich_context.model, resolved_files=(original, duplicate)),
    )

    result = manifest_xml_generator.generate(context)
    items = _items(result.document)

    assert len(items) == 3 + 2
    assert any("identical content" in d.message for d in result.diagnostics)


def test_no_duplicate_checksum_diagnostic_when_all_checksums_differ(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = manifest_xml_generator.generate(rich_context)

    assert not any("identical content" in d.message for d in result.diagnostics)


# --- unknown round label (defensive) ---------------------------------------------


def test_file_with_unknown_round_label_is_diagnosed_and_sorted_last(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    stray_file = replace(
        rich_context.model.resolved_files[0], round_label="5862df88-99d5-4237-b0ae-c5a2a02048f4"
    )
    files = (*rich_context.model.resolved_files, stray_file)
    context = replace(rich_context, model=replace(rich_context.model, resolved_files=files))

    result = manifest_xml_generator.generate(context)
    items = _items(result.document)
    file_hrefs = [_href(item) for item in items[3:]]

    assert file_hrefs[-1] == "files/5862df88-99d5-4237-b0ae-c5a2a02048f4/manuscript.docx"
    assert any("not in the round index" in d.message for d in result.diagnostics)


# --- multi-round generalization (ADR-013: synthetic 3-round fixture) ------------


def test_three_round_ordering_generalizes_latest_first_adr_013(
    manifest_xml_generator: ManifestXmlGenerator, rich_context: GeneratorContext
) -> None:
    rounds = (
        RoundInfo(label="Original", sequence_number=1, is_latest=False),
        RoundInfo(label="R1", sequence_number=2, is_latest=False),
        RoundInfo(label="R2", sequence_number=3, is_latest=True),
    )
    files = tuple(
        replace(rich_context.model.resolved_files[0], round_label=label, original_filename=label)
        for label in ("Original", "R1", "R2")
    )
    context = replace(
        rich_context, model=replace(rich_context.model, rounds=rounds, resolved_files=files)
    )

    items = _items(manifest_xml_generator.generate(context).document)
    file_hrefs = [_href(item) for item in items[3:]]

    assert file_hrefs == [
        "files/R2/manuscript.docx",
        "files/R1/manuscript.docx",
        "files/Original/manuscript.docx",
    ]


# --- malformed / edge-case ICAM ---------------------------------------------------


def test_every_optional_field_missing_still_produces_a_document(
    manifest_xml_generator: ManifestXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = manifest_xml_generator.generate(empty_context)

    assert result.document.xml_bytes
    assert len(_items(result.document)) == 3
