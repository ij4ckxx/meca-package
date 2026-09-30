"""Raw XML Generator — produces <ArticleID>_raw.xml (Business Rule Book §D, BR-036–050).

Implemented in Milestone 6B. See :class:`~meca_engine.generators.raw_xml.generator.RawXmlGenerator`
and :class:`~meca_engine.generators.raw_xml.document.RawXmlDocument`.
"""

from __future__ import annotations

from meca_engine.generators.raw_xml.document import RawXmlDocument
from meca_engine.generators.raw_xml.generator import RawXmlGenerator

__all__ = ["RawXmlDocument", "RawXmlGenerator"]
