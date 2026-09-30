"""Manifest XML Generator — produces <ArticleID>_manifest.xml (Business Rule Book §F, BR-076–095).

Implemented in Milestone 6D. See
:class:`~meca_engine.generators.manifest_xml.generator.ManifestXmlGenerator`,
:class:`~meca_engine.generators.manifest_xml.document.ManifestXmlDocument`,
and :mod:`~meca_engine.generators.manifest_xml.checksums` (the
Package-Builder-facing checksum interface, not wired into this
generator's own XML output).
"""

from __future__ import annotations

from meca_engine.generators.manifest_xml.document import ManifestXmlDocument
from meca_engine.generators.manifest_xml.generator import ManifestXmlGenerator

__all__ = ["ManifestXmlDocument", "ManifestXmlGenerator"]
