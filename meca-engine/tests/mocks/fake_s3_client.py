"""A fake, in-memory S3 client satisfying ``S3ClientProtocol``.

Per `tests/mocks/README.md` (Milestone 1): "Populated once
meca_engine.input... [is] implemented." This is that population — the
shared fake used by every S3Reader test, and available for later
milestones' integration/fault-injection tests too.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from meca_engine.input.readers.s3_reader import S3Entry, S3ObjectNotFoundError, S3TransientAPIError

if TYPE_CHECKING:
    from pathlib import Path


class FakeS3Client:
    """An in-memory stand-in for a real ``boto3`` S3 client.

    Objects are stored as ``{bucket: {key: bytes}}``. Supports injecting a
    transient-failure count for a specific key, to exercise
    ``S3ReadTransientError`` handling without any real network access.
    """

    def __init__(self) -> None:
        """Initialize an empty fake S3 client."""
        self._objects: dict[str, dict[str, bytes]] = {}
        self._transient_failures_remaining: dict[tuple[str, str], int] = {}
        self._transient_list_failures_remaining: dict[tuple[str, str], int] = {}

    def put_object(self, bucket: str, key: str, content: bytes) -> None:
        """Add an object to the fake store (test setup helper, not part of the protocol).

        Args:
            bucket: The bucket to store the object in.
            key: The object's full key.
            content: The object's bytes.
        """
        self._objects.setdefault(bucket, {})[key] = content

    def fail_next_read(self, bucket: str, key: str, *, times: int = 1) -> None:
        """Configure the next ``times`` reads of ``key`` to raise a transient error.

        Args:
            bucket: The bucket the key belongs to.
            key: The object key to fail reads for.
            times: How many consecutive reads should fail before succeeding.
        """
        self._transient_failures_remaining[(bucket, key)] = times

    def fail_next_list(self, bucket: str, prefix: str, *, times: int = 1) -> None:
        """Configure the next ``times`` listings of ``prefix`` to raise a transient error.

        Args:
            bucket: The bucket the prefix belongs to.
            prefix: The prefix to fail listings for.
            times: How many consecutive listing calls should fail before succeeding.
        """
        self._transient_list_failures_remaining[(bucket, prefix)] = times

    def _maybe_raise_transient(self, bucket: str, key: str) -> None:
        remaining = self._transient_failures_remaining.get((bucket, key), 0)
        if remaining > 0:
            self._transient_failures_remaining[(bucket, key)] = remaining - 1
            raise S3TransientAPIError(f"simulated transient failure for {bucket}/{key}")

    def _maybe_raise_transient_list(self, bucket: str, prefix: str) -> None:
        remaining = self._transient_list_failures_remaining.get((bucket, prefix), 0)
        if remaining > 0:
            self._transient_list_failures_remaining[(bucket, prefix)] = remaining - 1
            raise S3TransientAPIError(f"simulated transient list failure for {bucket}/{prefix}")

    def list_immediate_entries(self, bucket: str, prefix: str) -> tuple[S3Entry, ...]:
        """List only the immediate children of ``prefix``."""
        self._maybe_raise_transient_list(bucket, prefix)
        keys = self._objects.get(bucket)
        if keys is None:
            raise S3ObjectNotFoundError(f"no such bucket: {bucket}")
        matching = [key for key in keys if key.startswith(prefix)]
        if not matching:
            raise S3ObjectNotFoundError(f"no objects under prefix: {prefix}")

        seen_dirs: set[str] = set()
        entries: list[S3Entry] = []
        for key in matching:
            remainder = key[len(prefix) :]
            if "/" in remainder:
                dir_name = remainder.split("/", 1)[0]
                if dir_name not in seen_dirs:
                    seen_dirs.add(dir_name)
                    entries.append(S3Entry(name=dir_name, is_directory=True))
            elif remainder:
                entries.append(
                    S3Entry(name=remainder, is_directory=False, size_bytes=len(keys[key]))
                )
        return tuple(entries)

    def list_all_objects(self, bucket: str, prefix: str) -> tuple[S3Entry, ...]:
        """Recursively list every object under ``prefix``."""
        self._maybe_raise_transient_list(bucket, prefix)
        keys = self._objects.get(bucket)
        if keys is None:
            raise S3ObjectNotFoundError(f"no such bucket: {bucket}")
        matching = {key: value for key, value in keys.items() if key.startswith(prefix)}
        if not matching:
            raise S3ObjectNotFoundError(f"no objects under prefix: {prefix}")
        return tuple(
            S3Entry(name=key[len(prefix) :], is_directory=False, size_bytes=len(value))
            for key, value in matching.items()
        )

    def download_to(self, bucket: str, key: str, destination: Path) -> tuple[str, int]:
        """Write a stored object's bytes to ``destination``, computing its checksum."""
        self._maybe_raise_transient(bucket, key)
        keys = self._objects.get(bucket, {})
        if key not in keys:
            raise S3ObjectNotFoundError(f"no such key: {bucket}/{key}")
        content = keys[key]
        destination.write_bytes(content)
        return hashlib.sha256(content).hexdigest(), len(content)
