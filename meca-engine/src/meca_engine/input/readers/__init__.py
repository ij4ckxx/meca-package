"""Input Reader implementations.

:class:`~meca_engine.input.readers.base.InputReader` is the abstract
interface every concrete reader implements. Two concrete readers exist:
:class:`~meca_engine.input.readers.local_reader.LocalFolderReader` (local
development/testing) and
:class:`~meca_engine.input.readers.s3_reader.S3Reader` (production, per
ADR-019 — behind a pluggable :class:`~meca_engine.input.readers.s3_reader.S3ClientProtocol`
so the concrete AWS SDK integration can be mocked where infrastructure
decisions remain open).
"""

from __future__ import annotations

from meca_engine.input.readers.base import InputReader, TopLevelEntry
from meca_engine.input.readers.local_reader import LocalFolderReader
from meca_engine.input.readers.s3_reader import (
    Boto3S3Client,
    S3ClientProtocol,
    S3Entry,
    S3ObjectNotFoundError,
    S3Reader,
    S3TransientAPIError,
)

__all__ = [
    "Boto3S3Client",
    "InputReader",
    "S3ClientProtocol",
    "S3Entry",
    "S3ObjectNotFoundError",
    "S3Reader",
    "S3TransientAPIError",
    "LocalFolderReader",
    "TopLevelEntry",
]
