"""Checksum helpers used by the input/staging layer (and, later, output/).

Per 10_LLD_01_STRUCTURE_AND_PACKAGES.md §2.1: ``utils/hashing.py`` is the
one place streaming-checksum logic lives, shared rather than duplicated
across every module that needs to verify file integrity. Contains no
business logic — purely a generic, dependency-free streaming SHA-256
helper.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, BinaryIO

if TYPE_CHECKING:
    from pathlib import Path

_DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MiB


def compute_file_checksum(path: Path, *, chunk_size: int = _DEFAULT_CHUNK_SIZE) -> str:
    """Compute the SHA-256 checksum of a file already on disk.

    Reads the file in fixed-size chunks so memory use stays constant
    regardless of file size (13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md
    §9.3: binary attachments are never fully buffered in memory).

    Args:
        path: The file to checksum.
        chunk_size: Read buffer size in bytes.

    Returns:
        The lower-case hex-encoded SHA-256 digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_stream_checksum_while_copying(
    source: BinaryIO,
    destination: BinaryIO,
    *,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
) -> tuple[str, int]:
    """Copy a stream to another stream, computing a checksum as bytes flow through.

    Used by input readers to copy a file from its source (local disk or a
    remote object store) to the local staging workspace while computing
    the transferred bytes' checksum in the same pass — avoids a separate
    full re-read of the source purely for hashing.

    Args:
        source: The readable binary stream to copy from.
        destination: The writable binary stream to copy into.
        chunk_size: Read/write buffer size in bytes.

    Returns:
        A ``(checksum, bytes_transferred)`` tuple — the lower-case
        hex-encoded SHA-256 digest of everything written, and the total
        byte count transferred.
    """
    digest = hashlib.sha256()
    bytes_transferred = 0
    for chunk in iter(lambda: source.read(chunk_size), b""):
        digest.update(chunk)
        destination.write(chunk)
        bytes_transferred += len(chunk)
    return digest.hexdigest(), bytes_transferred
