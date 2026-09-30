"""Unit tests for meca_engine.generators.raw_xml.xslt_transform."""

from __future__ import annotations

import pytest

from meca_engine.exceptions import SourceXmlMalformedError
from meca_engine.generators.raw_xml.xslt_transform import transform

pytestmark = pytest.mark.unit

_MINIMAL_ARTICLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<article article-type="research-article">
  <front>
    <journal-meta>
      <journal-id journal-id-type="publisher-id">bcj</journal-id>
      <journal-title-group>
        <journal-title>Biochemical Journal</journal-title>
      </journal-title-group>
      <publisher><publisher-name>Portland Press Limited</publisher-name></publisher>
    </journal-meta>
    <article-meta>
      <title-group><article-title>A Study</article-title></title-group>
      <counts>
        <word-count count="100"/>
        <fig-count count="2"/>
        <table-count count="1"/>
        <equation-count count="0"/>
        <ref-count count="5"/>
        <page-count count="10"/>
      </counts>
    </article-meta>
  </front>
  <body><p>Hello.</p></body>
</article>
"""


def test_produces_well_formed_xml_with_doctype() -> None:
    result = transform(_MINIMAL_ARTICLE)

    assert result.startswith(b'<?xml version="1.0" encoding="UTF-8"?>')
    assert b"JATS (Z39.96) Journal Publishing DTD v1.3" in result
    assert b'dtd-version="1.3"' in result


def test_counts_reordered_to_fig_table_equation_ref_page_word() -> None:
    result = transform(_MINIMAL_ARTICLE)

    tags_in_order = [
        tag
        for tag in (
            b"<fig-count",
            b"<table-count",
            b"<equation-count",
            b"<ref-count",
            b"<page-count",
            b"<word-count",
        )
        if tag in result
    ]
    positions = [result.index(tag) for tag in tags_in_order]
    assert positions == sorted(positions)


def test_rejects_malformed_source_xml() -> None:
    with pytest.raises(SourceXmlMalformedError):
        transform(b"<article><unclosed></article>")


def test_internal_entity_is_never_expanded_into_output() -> None:
    """XXE hardening: an internal entity declaration must not resolve into the output."""
    xxe = (
        b'<?xml version="1.0"?>\n<!DOCTYPE article [\n<!ENTITY xxe "leaked-secret">\n]>\n'
        b'<article article-type="research-article">&xxe;</article>'
    )

    result = transform(xxe)

    assert b"leaked-secret" not in result
    assert b"xxe" not in result


def test_entity_expansion_bomb_does_not_expand() -> None:
    """XXE/DoS hardening: nested entity expansion must not blow up output size."""
    bomb = (
        b'<?xml version="1.0"?>\n<!DOCTYPE article [\n'
        b'<!ENTITY a "1234567890">\n'
        b'<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">\n'
        b'<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">\n'
        b"]>\n"
        b'<article article-type="research-article">&c;</article>'
    )

    result = transform(bomb)

    assert len(result) < 10_000
