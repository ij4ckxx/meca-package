"""Reusable XML writing infrastructure — Generator Framework (Milestone 6A).

No business logic, no JATS/MECA content mapping. Every future generator
builds its output through these modules — never through raw
:mod:`xml.etree.ElementTree` calls scattered across generator code —
so that namespace handling, attribute/element ordering, and encoding are
identical across all 5 generators.
"""

from __future__ import annotations
