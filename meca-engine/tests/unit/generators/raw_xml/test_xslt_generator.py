"""Unit tests for meca_engine.generators.raw_xml.xslt_generator."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from meca_engine.exceptions import GeneratorInvariantError
from meca_engine.generators.raw_xml.xslt_generator import XsltRawXmlGenerator

if TYPE_CHECKING:
    from meca_engine.generators.context import GeneratorContext

pytestmark = pytest.mark.unit

_SOURCE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<article article-type="research-article">
  <front>
    <journal-meta>
      <journal-id journal-id-type="publisher-id">bcj</journal-id>
      <journal-title-group><journal-title>Biochemical Journal</journal-title></journal-title-group>
      <publisher><publisher-name>Portland Press Limited</publisher-name></publisher>
    </journal-meta>
    <article-meta>
      <title-group><article-title>A Study</article-title></title-group>
    </article-meta>
  </front>
  <body><p>Hello.</p></body>
</article>
"""


def test_generates_raw_xml_from_source_bytes(rich_context: GeneratorContext) -> None:
    context = replace(rich_context, source_xml_bytes=_SOURCE_XML)
    generator = XsltRawXmlGenerator()

    result = generator.generate(context)

    assert result.document.article_id == context.model.identity.article_id
    assert result.document.filename == f"{context.model.identity.article_id}_raw.xml"
    assert b"Biochemical Journal" in result.document.xml_bytes


def test_generator_name_matches_raw_xml() -> None:
    assert XsltRawXmlGenerator().generator_name == "raw_xml"


def test_raises_when_source_xml_bytes_missing(rich_context: GeneratorContext) -> None:
    context = replace(rich_context, source_xml_bytes=None)
    generator = XsltRawXmlGenerator()

    with pytest.raises(GeneratorInvariantError, match="source_xml_bytes"):
        generator.generate(context)
