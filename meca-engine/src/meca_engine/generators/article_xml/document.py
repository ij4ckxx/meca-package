"""article.xml output document type — Milestone 6C.

The `T` in `ArticleXmlGenerator(BaseGenerator[ArticleXmlDocument])`
(11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.7).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArticleXmlDocument:
    """The generated article.xml document, ready to write to a package.

    Attributes:
        article_id: The article this document was generated for.
        filename: BR-073's ``<ArticleID>_article.xml`` filename pattern.
        xml_bytes: The complete, serialized document.
    """

    article_id: str
    filename: str
    xml_bytes: bytes
