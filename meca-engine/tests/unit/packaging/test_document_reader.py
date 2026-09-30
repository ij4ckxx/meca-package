"""Unit tests for meca_engine.packaging.document_reader."""

from __future__ import annotations

import pytest

from meca_engine.exceptions.article_errors import GeneratorInvariantError
from meca_engine.generators.xml.namespaces import NamespaceManager
from meca_engine.packaging.document_reader import extract_generated_doi, extract_packaged_file_hrefs

pytestmark = pytest.mark.unit

_MANIFEST_URI = "https://manuscriptexchange.org/schema/manifest"
_XLINK_URI = "http://www.w3.org/1999/xlink"


@pytest.fixture
def namespace_manager() -> NamespaceManager:
    return NamespaceManager({"meca-manifest": _MANIFEST_URI, "xlink": _XLINK_URI})


def _manifest_bytes(*, extra_items: str = "") -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest xmlns="{_MANIFEST_URI}" xmlns:xlink="{_XLINK_URI}">
  <item id="item-article" item-type="article-metadata">
    <instance media-type="application/xml" xlink:href="CS-2025-6808_article.xml"/>
  </item>
  <item id="item-reviews" item-type="review-metadata">
    <instance media-type="application/xml" xlink:href="CS-2025-6808_reviews.xml"/>
  </item>
  <item id="item-transfer" item-type="transfer-metadata">
    <instance media-type="application/xml" xlink:href="CS-2025-6808_transfer.xml"/>
  </item>
  {extra_items}
</manifest>""".encode()


def test_extract_packaged_file_hrefs_excludes_fixed_items(
    namespace_manager: NamespaceManager,
) -> None:
    hrefs = extract_packaged_file_hrefs(_manifest_bytes(), namespace_manager)

    assert hrefs == ()


def test_extract_packaged_file_hrefs_returns_file_items_in_document_order(
    namespace_manager: NamespaceManager,
) -> None:
    extra = """
  <item id="file-1" item-type="figure">
    <instance media-type="image/jpeg" xlink:href="files/R1/fig1.jpg"/>
  </item>
  <item id="file-2" item-type="supplementary-material">
    <instance media-type="application/pdf" xlink:href="files/Original/supp1.pdf"/>
  </item>
"""
    hrefs = extract_packaged_file_hrefs(_manifest_bytes(extra_items=extra), namespace_manager)

    assert hrefs == ("files/R1/fig1.jpg", "files/Original/supp1.pdf")


def test_extract_packaged_file_hrefs_skips_an_item_with_no_instance_element(
    namespace_manager: NamespaceManager,
) -> None:
    extra = """
  <item id="file-1" item-type="figure">
    <instance media-type="image/jpeg" xlink:href="files/R1/fig1.jpg"/>
  </item>
  <item id="file-2" item-type="corrupt"/>
"""
    hrefs = extract_packaged_file_hrefs(_manifest_bytes(extra_items=extra), namespace_manager)

    assert hrefs == ("files/R1/fig1.jpg",)


def test_extract_packaged_file_hrefs_raises_for_unregistered_namespace() -> None:
    empty_namespace_manager = NamespaceManager({})

    with pytest.raises(GeneratorInvariantError):
        extract_packaged_file_hrefs(_manifest_bytes(), empty_namespace_manager)


def test_extract_generated_doi_returns_the_doi_typed_article_id() -> None:
    article_xml = b"""<?xml version="1.0" encoding="utf-8"?>
<article>
  <front>
    <article-meta>
      <article-id pub-id-type="publisher-id">CS20256808</article-id>
      <article-id pub-id-type="doi">10.1042/cs20256808</article-id>
    </article-meta>
  </front>
</article>"""

    assert extract_generated_doi(article_xml) == "10.1042/cs20256808"


def test_extract_generated_doi_returns_none_when_absent() -> None:
    article_xml = b"""<?xml version="1.0" encoding="utf-8"?>
<article>
  <front>
    <article-meta>
      <article-id pub-id-type="publisher-id">CS20256808</article-id>
    </article-meta>
  </front>
</article>"""

    assert extract_generated_doi(article_xml) is None
