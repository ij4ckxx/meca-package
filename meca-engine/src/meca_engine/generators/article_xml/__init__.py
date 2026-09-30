"""Article XML Generator — produces <ArticleID>_article.xml (Business Rule Book §E, BR-051–075).

Implemented in Milestone 6C. See
:class:`~meca_engine.generators.article_xml.generator.ArticleXmlGenerator`
and :class:`~meca_engine.generators.article_xml.document.ArticleXmlDocument`.
"""

from __future__ import annotations

from meca_engine.generators.article_xml.document import ArticleXmlDocument
from meca_engine.generators.article_xml.generator import ArticleXmlGenerator

__all__ = ["ArticleXmlDocument", "ArticleXmlGenerator"]
