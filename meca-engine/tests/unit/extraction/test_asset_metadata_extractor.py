"""Unit tests for meca_engine.extraction.asset_metadata_extractor."""

from __future__ import annotations

from pathlib import Path

import pytest

from meca_engine.extraction.asset_metadata_extractor import extract_asset_metadata
from meca_engine.extraction.parsed_model import (
    EncodingInfo,
    ParsedAttribute,
    ParsedDocument,
    ParsedElement,
)

pytestmark = pytest.mark.unit

_ENCODING = EncodingInfo(declared_encoding=None, bom_encoding=None, effective_encoding="utf-8")
_XLINK_NS = "http://www.w3.org/1999/xlink"


def _document(root: ParsedElement) -> ParsedDocument:
    return ParsedDocument(source_path=Path("test.xml"), encoding=_ENCODING, doctype=None, root=root)


def test_extracts_figure_with_label_and_file_reference() -> None:
    graphic = ParsedElement(
        tag="graphic",
        namespace_uri=None,
        attributes=(ParsedAttribute("href", _XLINK_NS, "fig1.jpg"),),
    )
    label = ParsedElement(tag="label", namespace_uri=None, text="Figure 1")
    fig = ParsedElement(
        tag="fig",
        namespace_uri=None,
        attributes=(ParsedAttribute("id", None, "f1"),),
        children=(label, graphic),
    )
    root = ParsedElement(tag="root", namespace_uri=None, children=(fig,))

    metadata, diagnostics = extract_asset_metadata(_document(root))

    assert len(metadata.assets) == 1
    asset = metadata.assets[0]
    assert asset.asset_tag == "fig"
    assert asset.element_id == "f1"
    assert asset.label == "Figure 1"
    assert len(asset.file_references) == 1
    assert asset.file_references[0].value == "fig1.jpg"
    assert diagnostics == ()


def test_recognizes_every_default_asset_tag() -> None:
    tags = (
        "fig",
        "table-wrap",
        "supplementary-material",
        "disp-formula",
        "inline-formula",
        "media",
    )
    root = ParsedElement(
        tag="root",
        namespace_uri=None,
        children=tuple(ParsedElement(tag=tag, namespace_uri=None) for tag in tags),
    )

    metadata, _ = extract_asset_metadata(_document(root))

    assert {a.asset_tag for a in metadata.assets} == set(tags)


def test_custom_asset_tag_names() -> None:
    root = ParsedElement(
        tag="root", namespace_uri=None, children=(ParsedElement(tag="chart", namespace_uri=None),)
    )

    metadata, _ = extract_asset_metadata(_document(root), asset_tag_names=("chart",))

    assert len(metadata.assets) == 1
    assert metadata.assets[0].asset_tag == "chart"


def test_asset_without_file_reference_has_empty_tuple() -> None:
    fig = ParsedElement(tag="fig", namespace_uri=None)
    root = ParsedElement(tag="root", namespace_uri=None, children=(fig,))

    metadata, _ = extract_asset_metadata(_document(root))

    assert metadata.assets[0].file_references == ()


def test_no_assets_produces_empty_metadata() -> None:
    root = ParsedElement(tag="root", namespace_uri=None)

    metadata, diagnostics = extract_asset_metadata(_document(root))

    assert metadata.assets == ()
    assert diagnostics == ()
