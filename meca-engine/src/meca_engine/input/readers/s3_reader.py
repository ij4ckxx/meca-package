"""Amazon S3 Reader, behind a pluggable client interface.

Per the current task's explicit allowance ("concrete AWS integration may
be mocked if blocked by infrastructure decisions"): the concrete AWS SDK
(``boto3``) dependency is optional (see ``pyproject.toml``'s ``[project.
optional-dependencies].aws`` group) and is only imported lazily, inside
:class:`Boto3S3Client`, so the core package installs and the rest of this
module remains fully importable/testable without it. Which concrete
backend technology / bucket layout / credentials strategy production uses
is still an open engineering question (16_LLD_07_READINESS_ASSESSMENT.md
§15.2 TQ-03/TQ-04, ADR-019) — this module implements the reader
*interface* against that eventual decision, not the decision itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from meca_engine.exceptions import S3ReadTransientError, SourceUnavailableError
from meca_engine.input.models import BatchSource, FileRecord, S3BatchSource
from meca_engine.input.readers.base import InputReader, TopLevelEntry

if TYPE_CHECKING:
    from pathlib import Path

_STAGE = "meca_engine.input.readers.s3_reader"


class S3ObjectNotFoundError(Exception):
    """Signal raised by an :class:`S3ClientProtocol` implementation: key/prefix not found.

    Internal adapter-boundary contract only — never propagates outside
    :class:`S3Reader`, which translates it into the approved
    :class:`~meca_engine.exceptions.SourceUnavailableError`. Not a
    :class:`~meca_engine.exceptions.MecaEngineError` subclass, since it is
    plumbing for a swappable low-level client, not an engine-level
    business exception.
    """


class S3TransientAPIError(Exception):
    """Signal raised by an :class:`S3ClientProtocol` implementation: transient API failure.

    Translated by :class:`S3Reader` into
    :class:`~meca_engine.exceptions.S3ReadTransientError`. See
    :class:`S3ObjectNotFoundError` for why this is not itself a
    :class:`~meca_engine.exceptions.MecaEngineError` subclass.
    """


@dataclass(frozen=True)
class S3Entry:
    """One entry returned by an S3 listing operation.

    Attributes:
        name: The entry's basename (no prefix, no trailing slash).
        is_directory: Whether this is a common-prefix ("folder") or an object.
        size_bytes: The object's size, or ``None`` for a directory entry.
    """

    name: str
    is_directory: bool
    size_bytes: int | None = None


class S3ClientProtocol(Protocol):
    """The minimal S3 operations :class:`S3Reader` needs.

    Modeled directly on real S3 semantics (a delimiter=``"/"`` listing for
    immediate children, an undelimited listing for a full recursive
    subtree, and a single-object download) so a real ``boto3``-backed
    implementation is a thin, mechanical adapter.
    """

    def list_immediate_entries(self, bucket: str, prefix: str) -> tuple[S3Entry, ...]:
        """List only the immediate children of ``prefix`` (like ``Delimiter="/"``)."""
        ...

    def list_all_objects(self, bucket: str, prefix: str) -> tuple[S3Entry, ...]:
        """Recursively list every object under ``prefix`` (no delimiter)."""
        ...

    def download_to(self, bucket: str, key: str, destination: Path) -> tuple[str, int]:
        """Download one object's bytes to ``destination``, returning (checksum, size)."""
        ...


class Boto3S3Client:
    """A real S3 client backed by ``boto3``, imported lazily.

    Raises a clear, batch-level :class:`~meca_engine.exceptions.ConfigurationError`
    at construction time if ``boto3`` is not installed — installing the
    ``aws`` optional dependency group (``pip install -e ".[aws]"``) is
    required to actually use this class. Nothing else in this module
    requires ``boto3`` to be present.
    """

    def __init__(self) -> None:
        """Construct a real boto3-backed S3 client.

        Raises:
            ConfigurationError: If the ``boto3`` package is not installed.
        """
        try:
            import boto3  # noqa: F401  (import-only availability check)
        except ImportError as exc:
            from meca_engine.exceptions import ConfigurationError

            raise ConfigurationError(
                "boto3 is required to use Boto3S3Client but is not installed. "
                'Install it with: pip install -e ".[aws]"',
                stage=_STAGE,
                inner_cause=exc,
            ) from exc
        import boto3  # pragma: no cover

        self._client = boto3.client("s3")  # pragma: no cover

    def list_immediate_entries(self, bucket: str, prefix: str) -> tuple[S3Entry, ...]:
        """List only the immediate children of ``prefix``."""
        return self._list(bucket, prefix, delimiter="/")  # pragma: no cover

    def list_all_objects(self, bucket: str, prefix: str) -> tuple[S3Entry, ...]:
        """Recursively list every object under ``prefix``."""
        return self._list(bucket, prefix, delimiter="")  # pragma: no cover

    def _list(
        self, bucket: str, prefix: str, *, delimiter: str
    ) -> tuple[S3Entry, ...]:  # pragma: no cover
        # Requires a real boto3/botocore installation to exercise — see
        # ADR-019/TQ-04 (16_LLD_07_READINESS_ASSESSMENT.md §15.2) and the
        # current task's explicit allowance that "concrete AWS integration
        # may be mocked if blocked by infrastructure decisions". Every
        # branch of S3Reader's own translation logic (SourceUnavailableError
        # vs S3ReadTransientError) IS covered, against FakeS3Client, in
        # tests/unit/input/test_s3_reader.py — only this thin, mechanical
        # boto3 adapter is excluded from the coverage target.
        from botocore.exceptions import ClientError

        entries: list[S3Entry] = []
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter=delimiter):
                for common_prefix in page.get("CommonPrefixes", []):
                    full = common_prefix["Prefix"]
                    name = full[len(prefix) :].rstrip("/")
                    entries.append(S3Entry(name=name, is_directory=True))
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key == prefix:
                        continue
                    name = key[len(prefix) :]
                    entries.append(S3Entry(name=name, is_directory=False, size_bytes=obj["Size"]))
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in {"NoSuchKey", "NoSuchBucket", "404"}:
                raise S3ObjectNotFoundError(str(exc)) from exc
            raise S3TransientAPIError(str(exc)) from exc
        return tuple(entries)

    def download_to(
        self, bucket: str, key: str, destination: Path
    ) -> tuple[str, int]:  # pragma: no cover
        """Download one object's bytes to ``destination``.

        Requires a real boto3/botocore installation to exercise — see the
        ``_list`` docstring above for why this is excluded from coverage.
        """
        from botocore.exceptions import ClientError

        from meca_engine.utils.hashing import compute_stream_checksum_while_copying

        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
            with destination.open("wb") as dest_stream:
                return compute_stream_checksum_while_copying(response["Body"], dest_stream)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in {"NoSuchKey", "NoSuchBucket", "404"}:
                raise S3ObjectNotFoundError(str(exc)) from exc
            raise S3TransientAPIError(str(exc)) from exc


def _require_s3_source(source: BatchSource) -> S3BatchSource:
    if not isinstance(source, S3BatchSource):
        raise TypeError(f"S3Reader requires an S3BatchSource, got {type(source).__name__}")
    return source


class S3Reader(InputReader):
    """Reads batches of articles from Amazon S3, via a pluggable client.

    Attributes:
        client: The :class:`S3ClientProtocol` implementation to use — a
            real :class:`Boto3S3Client`, or a fake/in-memory test double.
    """

    def __init__(self, client: S3ClientProtocol) -> None:
        """Initialize the reader with a concrete S3 client implementation.

        Args:
            client: Any object satisfying :class:`S3ClientProtocol`.
        """
        self.client = client

    def list_batch_article_ids(self, source: BatchSource) -> tuple[str, ...]:
        """List every article "folder" (common prefix) directly under the batch prefix."""
        s3_source = _require_s3_source(source)
        entries = self._list_immediate(s3_source.bucket, s3_source.prefix, article_id=None)
        return tuple(sorted(entry.name for entry in entries if entry.is_directory))

    def list_article_top_level(
        self, article_id: str, source: BatchSource
    ) -> tuple[TopLevelEntry, ...]:
        """List the entries directly under one article's own prefix."""
        s3_source = _require_s3_source(source)
        article_prefix = f"{s3_source.prefix}{article_id}/"
        entries = self._list_immediate(s3_source.bucket, article_prefix, article_id=article_id)
        result = sorted(
            (TopLevelEntry(name=e.name, is_directory=e.is_directory) for e in entries),
            key=lambda item: item.name,
        )
        return tuple(result)

    def list_round_files(
        self, article_id: str, round_label: str, source: BatchSource
    ) -> tuple[FileRecord, ...]:
        """List every object under one article's one round prefix, recursively."""
        s3_source = _require_s3_source(source)
        round_prefix = f"{s3_source.prefix}{article_id}/{round_label}/"
        try:
            entries = self.client.list_all_objects(s3_source.bucket, round_prefix)
        except S3ObjectNotFoundError as exc:
            raise SourceUnavailableError(
                f"Round prefix does not exist: s3://{s3_source.bucket}/{round_prefix}",
                article_id=article_id,
                stage=_STAGE,
                inner_cause=exc,
            ) from exc
        except S3TransientAPIError as exc:
            raise S3ReadTransientError(
                f"Transient S3 failure listing s3://{s3_source.bucket}/{round_prefix}",
                article_id=article_id,
                stage=_STAGE,
                inner_cause=exc,
            ) from exc
        return tuple(
            FileRecord(round_label=round_label, relative_path=e.name, size_bytes=e.size_bytes or 0)
            for e in entries
            if not e.is_directory
        )

    def fetch_file(
        self,
        article_id: str,
        round_label: str,
        relative_path: str,
        source: BatchSource,
        destination: Path,
    ) -> tuple[str, int]:
        """Download one file's bytes from S3 into a local destination path."""
        s3_source = _require_s3_source(source)
        key = f"{s3_source.prefix}{article_id}/{round_label}/{relative_path}"
        try:
            return self.client.download_to(s3_source.bucket, key, destination)
        except S3ObjectNotFoundError as exc:
            raise SourceUnavailableError(
                f"Object does not exist: s3://{s3_source.bucket}/{key}",
                article_id=article_id,
                stage=_STAGE,
                inner_cause=exc,
            ) from exc
        except S3TransientAPIError as exc:
            raise S3ReadTransientError(
                f"Transient S3 failure downloading s3://{s3_source.bucket}/{key}",
                article_id=article_id,
                stage=_STAGE,
                inner_cause=exc,
            ) from exc

    def _list_immediate(
        self, bucket: str, prefix: str, *, article_id: str | None
    ) -> tuple[S3Entry, ...]:
        try:
            return self.client.list_immediate_entries(bucket, prefix)
        except S3ObjectNotFoundError as exc:
            raise SourceUnavailableError(
                f"Prefix does not exist: s3://{bucket}/{prefix}",
                article_id=article_id,
                stage=_STAGE,
                inner_cause=exc,
            ) from exc
        except S3TransientAPIError as exc:
            raise S3ReadTransientError(
                f"Transient S3 failure listing s3://{bucket}/{prefix}",
                article_id=article_id,
                stage=_STAGE,
                inner_cause=exc,
            ) from exc
