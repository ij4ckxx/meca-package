"""TransferXmlDocument — the TransferXmlGenerator's output type."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransferXmlDocument:
    """The generated transfer.xml, ready to write to the package.

    Attributes:
        article_id: The article this transfer.xml was generated for.
        filename: BR-139's ``<ArticleID>_transfer.xml`` pattern.
        xml_bytes: The complete, serialized document.
    """

    article_id: str
    filename: str
    xml_bytes: bytes
