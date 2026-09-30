"""Input-layer immutable models.

These are input-layer models only, entirely separate from the Internal
Canonical Article Model (ICAM, 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §3)
— the ICAM does not exist until Milestone 3's Metadata Extractor parses the
Kriyadocs XML. Everything here is derived purely from filesystem/object-store
*structure* (paths, names, sizes, checksums), never from XML content.

All models are frozen dataclasses: once discovery or staging produces one,
it is never mutated — later pipeline stages build new objects rather than
patching these in place, consistent with the ICAM's own immutability
philosophy (11_LLD_02... §3.7) applied one layer earlier.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path


class BatchSource:
    """Marker base for "where a batch of articles comes from".

    Concrete subclasses are pure data (no I/O) — the actual reading
    happens in :mod:`meca_engine.input.readers`, which is handed a
    ``BatchSource`` and knows how to interpret it. Deliberately not an
    ``ABC``: it declares no abstract methods (it is a marker/type-only
    base, not a behavioral contract), and an ``ABC`` with zero abstract
    members is a lint smell (ruff B024) rather than a meaningful
    safeguard.
    """


@dataclass(frozen=True)
class LocalBatchSource(BatchSource):
    """A batch whose articles are subfolders of a local directory.

    Attributes:
        root_path: The local directory containing one subfolder per
            article (matching the Reverse Engineering Report's observed
            input shape: ``<root>/<ArticleID>/...``).
    """

    root_path: Path


@dataclass(frozen=True)
class S3BatchSource(BatchSource):
    """A batch whose articles are common-prefixed objects in an S3 bucket.

    Attributes:
        bucket: The S3 bucket name.
        prefix: The key prefix under which each article has its own
            "subfolder" (S3 common-prefix), mirroring ``LocalBatchSource``'s
            shape (ADR-019).
    """

    bucket: str
    prefix: str


@dataclass(frozen=True)
class FileRecord:
    """One file belonging to one article, at whatever stage of processing.

    Before staging, ``checksum`` and ``staged_local_path`` are ``None``
    (enumeration only lists what exists and its size — it never opens a
    file's content). After staging, both are populated.

    Attributes:
        round_label: The submission-round folder name this file was found
            under (an opaque string — no round-naming convention is
            assumed, per ADR-014).
        relative_path: The file's path relative to its round folder,
            using forward slashes regardless of host OS.
        size_bytes: The file's size as reported by the source listing
            (S3 object size, or local ``stat().st_size``).
        checksum: The SHA-256 checksum computed during/after staging, or
            ``None`` if this record has not yet been staged.
        staged_local_path: The absolute local path this file was copied
            to during staging, or ``None`` if not yet staged.
    """

    round_label: str
    relative_path: str
    size_bytes: int
    checksum: str | None = None
    staged_local_path: Path | None = None

    def with_staging_result(self, *, checksum: str, staged_local_path: Path) -> FileRecord:
        """Return a new record with staging results filled in.

        Args:
            checksum: The computed SHA-256 checksum of the staged copy.
            staged_local_path: Where the staged copy now lives.

        Returns:
            A new, otherwise-identical :class:`FileRecord` with
            ``checksum`` and ``staged_local_path`` populated.
        """
        return FileRecord(
            round_label=self.round_label,
            relative_path=self.relative_path,
            size_bytes=self.size_bytes,
            checksum=checksum,
            staged_local_path=staged_local_path,
        )


@dataclass(frozen=True)
class FileInventory:
    """The complete set of files discovered (and, later, staged) for one article.

    Attributes:
        files: Every file record, across every round.
        anomalous_relative_paths: Relative paths (``"<round>/<path>"``)
            flagged as technically anomalous during enumeration — e.g. a
            zero-byte file, or a known OS-artifact filename (``.DS_Store``,
            ``Thumbs.db``). This is a purely technical/hygiene signal, not
            the business-rule-driven "which files are actually part of
            the submission" determination — that remains
            Milestone 3's Metadata Extractor / File Resolver
            responsibility (Business Rule Book BR-011/BR-014), which is
            driven by the source XML's custom-meta file entries, not
            available here.
    """

    files: tuple[FileRecord, ...] = field(default_factory=tuple)
    anomalous_relative_paths: tuple[str, ...] = field(default_factory=tuple)

    @property
    def total_size_bytes(self) -> int:
        """Return the sum of every file's ``size_bytes``."""
        return sum(f.size_bytes for f in self.files)

    def by_round(self, round_label: str) -> tuple[FileRecord, ...]:
        """Return every file record belonging to one round.

        Args:
            round_label: The round to filter by.

        Returns:
            The matching file records, in enumeration order.
        """
        return tuple(f for f in self.files if f.round_label == round_label)

    @property
    def round_labels(self) -> tuple[str, ...]:
        """Return every distinct round label present, in first-seen order."""
        seen: list[str] = []
        for record in self.files:
            if record.round_label not in seen:
                seen.append(record.round_label)
        return tuple(seen)


@dataclass(frozen=True)
class ArticleReference:
    """An abstract reference to one article's location — never parsed content.

    Produced by :mod:`meca_engine.input.discovery`. Per the current task's
    explicit requirement, readers/discovery return references like this
    one, never parsed XML or extracted metadata.

    Attributes:
        article_id: The exact article folder/prefix name, preserved
            verbatim (Business Rule Book BR-003 — casing and punctuation
            unchanged).
        source: Where this article was discovered (local or S3).
        root_xml_relative_name: The single root-level XML-named file's
            name (existence-checked only — never opened or parsed; the
            content well-formedness check is Milestone 3's responsibility).
        file_inventory: Every file discovered under this article's round
            folders, with sizes but no checksums yet.
        discovered_at: When this reference was produced.
    """

    article_id: str
    source: BatchSource
    root_xml_relative_name: str
    file_inventory: FileInventory
    discovered_at: datetime


@dataclass(frozen=True)
class DiscoveryFailure:
    """One article (or the batch root itself) that failed discovery-time validation.

    Attributes:
        article_id: The article this failure pertains to, or ``None`` if
            the failure occurred before any article could be identified
            (e.g. the batch root itself does not exist).
        reason: A short, human-readable description of the failure.
        exception_type: The ``type(...).__name__`` of the exception that
            was raised and caught for this article, for structured
            logging/reporting.
    """

    article_id: str | None
    reason: str
    exception_type: str


@dataclass(frozen=True)
class Batch:
    """The result of discovering one batch: successes and failures alike.

    Attributes:
        batch_id: A human-readable identifier for this discovery run
            (not a business identifier — purely for logging/correlation).
        source: The batch source that was scanned.
        article_refs: Every article that passed discovery-time structural
            validation, ready to be staged.
        discovery_failures: Every article (or batch-root-level) failure
            encountered during the scan — per ADR-009's "isolate failures
            per article" principle, one bad article's discovery failure
            never prevents the rest of the batch from being discovered.
        discovered_at: When this discovery pass completed.
    """

    batch_id: str
    source: BatchSource
    article_refs: tuple[ArticleReference, ...]
    discovery_failures: tuple[DiscoveryFailure, ...]
    discovered_at: datetime


@dataclass(frozen=True)
class StagedArticle:
    """One article whose files have been copied into a local working directory.

    Attributes:
        article_id: The article this staged copy belongs to.
        working_directory: The local directory this article was staged
            into (13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md §9.4).
        source: Where this article was staged from.
        file_inventory: Every staged file, now with ``checksum`` and
            ``staged_local_path`` populated.
        staged_at: When staging completed successfully.
    """

    article_id: str
    working_directory: Path
    source: BatchSource
    file_inventory: FileInventory
    staged_at: datetime
