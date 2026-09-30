"""raw.xml output document type — Milestone 6B.

The `T` in `RawXmlGenerator(BaseGenerator[RawXmlDocument])`
(11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.7).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawXmlDocument:
    """The generated raw.xml document, ready to write to a package.

    Attributes:
        article_id: The article this document was generated for.
        filename: BR-048's ``<ArticleID>_raw.xml`` filename pattern.
        xml_bytes: The complete, serialized document.
    """

    article_id: str
    filename: str
    xml_bytes: bytes
