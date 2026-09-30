"""ManifestXmlDocument — the ManifestXmlGenerator's output type."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ManifestXmlDocument:
    """The generated manifest.xml, ready to write to the package.

    Attributes:
        article_id: The article this manifest.xml was generated for.
        filename: BR-088's ``<ArticleID>_manifest.xml`` pattern.
        xml_bytes: The complete, serialized document.
    """

    article_id: str
    filename: str
    xml_bytes: bytes
