"""Checksum framework — interface only, NOT wired into manifest.xml's XML output.

**Boundary**: direct inspection of all 3 real reference packages'
manifest.xml confirms 0/3 carry a checksum or size attribute on any
``<instance>`` element — the NISO MECA Manifest DTD v1.0 this generator
targets (BR-076) does not represent file integrity data in manifest.xml
itself. Verifying/recording checksums as files are written into the
final package zip is therefore the **Package Builder** milestone's
responsibility, not this generator's — this module defines the
interface that milestone will implement against, without this generator
calling it or emitting anything checksum-related into its own XML
output. See the Manifest Decision Log's "Checksum Responsibility" entry.

The one algorithm currently supported (:class:`Sha256PassthroughChecksum`)
does not compute anything itself — it forwards
:attr:`~meca_engine.model.article.ResolvedFile.checksum`, already
computed once (SHA-256, via
:func:`meca_engine.utils.hashing.compute_file_checksum`) during
Milestone 5B's file resolution. A future second algorithm (e.g. MD5, for
a destination system that requires it) would implement this same
:class:`ChecksumAlgorithm` protocol without this generator's own code
changing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from meca_engine.model.article import ResolvedFile


class ChecksumAlgorithm(Protocol):
    """A pluggable checksum algorithm a future Package Builder can select."""

    def compute(self, resolved_file: ResolvedFile) -> str:
        """Return ``resolved_file``'s checksum under this algorithm."""
        ...


class Sha256PassthroughChecksum:
    """Returns the ICAM's already-computed SHA-256 checksum, unchanged."""

    def compute(self, resolved_file: ResolvedFile) -> str:
        """Return ``resolved_file.checksum`` verbatim."""
        return resolved_file.checksum


DEFAULT_CHECKSUM_ALGORITHM: ChecksumAlgorithm = Sha256PassthroughChecksum()
