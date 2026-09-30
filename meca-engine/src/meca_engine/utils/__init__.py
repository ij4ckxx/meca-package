"""Small, dependency-free helpers shared across packages.

Must never contain business logic.

**Partially implemented as of Milestone 2.** ``hashing.py`` (checksum
helpers for the Input & Staging Layer) is implemented — see
10_LLD_01_STRUCTURE_AND_PACKAGES.md §2.1. ``xml_utils.py`` (XML
pretty-printing/escaping helpers for the generators) remains an
unimplemented stub, deferred to the milestone that implements the
generators (`08_IMPLEMENTATION_ROADMAP.md` Phase 4).
"""

from __future__ import annotations

from meca_engine.utils.hashing import compute_file_checksum, compute_stream_checksum_while_copying

__all__ = [
    "compute_file_checksum",
    "compute_stream_checksum_while_copying",
]
