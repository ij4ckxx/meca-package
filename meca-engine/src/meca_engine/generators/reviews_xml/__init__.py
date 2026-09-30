"""Reviews XML Generator — produces <ArticleID>_reviews.xml (Business Rule Book §G, BR-096–125).

Implemented in Milestone 6F. See
:class:`~meca_engine.generators.reviews_xml.generator.ReviewsXmlGenerator`,
:class:`~meca_engine.generators.reviews_xml.document.ReviewsXmlDocument`,
:mod:`~meca_engine.generators.reviews_xml.review_builder`, and
:mod:`~meca_engine.generators.reviews_xml.decision_builder`.
"""

from __future__ import annotations

from meca_engine.generators.reviews_xml.document import ReviewsXmlDocument
from meca_engine.generators.reviews_xml.generator import ReviewsXmlGenerator

__all__ = ["ReviewsXmlDocument", "ReviewsXmlGenerator"]
