"""ReviewsXmlDocument — the ReviewsXmlGenerator's output type."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewsXmlDocument:
    """The generated reviews.xml, ready to write to the package.

    Attributes:
        article_id: The article this reviews.xml was generated for.
        filename: BR-122's ``<ArticleID>_reviews.xml`` pattern.
        xml_bytes: The complete, serialized document.
    """

    article_id: str
    filename: str
    xml_bytes: bytes
