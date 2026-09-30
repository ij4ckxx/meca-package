"""Transfer XML Generator — produces <ArticleID>_transfer.xml (Business Rule Book §H, BR-126–140).

Implemented in Milestone 6G. See
:class:`~meca_engine.generators.transfer_xml.generator.TransferXmlGenerator`
and :class:`~meca_engine.generators.transfer_xml.document.TransferXmlDocument`.
"""

from __future__ import annotations

from meca_engine.generators.transfer_xml.document import TransferXmlDocument
from meca_engine.generators.transfer_xml.generator import TransferXmlGenerator

__all__ = ["TransferXmlDocument", "TransferXmlGenerator"]
