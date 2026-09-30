"""Input Reader abstract interface.

Per 05_SYSTEM_MODULE_BREAKDOWN.md §2 and the current task's requirement
that "readers must return abstract article references, not parsed
content": every method here deals only in names, sizes, and byte streams
— never in parsed XML or extracted metadata. Concrete implementations:
:class:`~meca_engine.input.readers.local_reader.LocalFolderReader` and
:class:`~meca_engine.input.readers.s3_reader.S3Reader`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.input.models import BatchSource, FileRecord


@dataclass(frozen=True)
class TopLevelEntry:
    """One entry directly under an article's own root (a file or a "folder").

    For a local source this is a literal filesystem entry; for an S3
    source, "folders" are simulated via common-prefix listing (objects
    sharing a ``/``-delimited prefix).

    Attributes:
        name: The entry's name (no path separators).
        is_directory: Whether this entry represents a submission-round
            folder (``True``) or a single file (``False``, e.g. the
            candidate root XML file).
    """

    name: str
    is_directory: bool


class InputReader(ABC):
    """Low-level source access: discovery, enumeration, and byte transfer.

    Deliberately minimal — an ``InputReader`` never validates article
    *structure* (that is :mod:`meca_engine.input.discovery`'s job) and
    never manages a local workspace (that is
    :mod:`meca_engine.input.staging`'s job). It only knows how to list and
    fetch bytes from one kind of source.
    """

    @abstractmethod
    def list_batch_article_ids(self, source: BatchSource) -> tuple[str, ...]:
        """List every candidate article id directly under the batch root.

        Args:
            source: The batch source to list.

        Returns:
            Candidate article ids (folder/common-prefix names), in the
            order the underlying source returns them — callers must not
            assume any particular ordering.

        Raises:
            SourceUnavailableError: If the batch root itself cannot be
                accessed (does not exist, or access was denied).
        """

    @abstractmethod
    def list_article_top_level(
        self, article_id: str, source: BatchSource
    ) -> tuple[TopLevelEntry, ...]:
        """List the entries directly under one article's own root.

        Args:
            article_id: The article to list.
            source: The batch source it belongs to.

        Returns:
            Every top-level entry (candidate root XML file(s) and round
            folder(s)) found directly under this article's root.

        Raises:
            SourceUnavailableError: If this specific article's root
                cannot be accessed.
        """

    @abstractmethod
    def list_round_files(
        self, article_id: str, round_label: str, source: BatchSource
    ) -> tuple[FileRecord, ...]:
        """List every file under one article's one round folder, recursively.

        Args:
            article_id: The article the round belongs to.
            round_label: The round folder name to list.
            source: The batch source it belongs to.

        Returns:
            One :class:`~meca_engine.input.models.FileRecord` per file
            found (``checksum`` and ``staged_local_path`` left ``None`` —
            this call never reads file content).
        """

    @abstractmethod
    def fetch_file(
        self,
        article_id: str,
        round_label: str,
        relative_path: str,
        source: BatchSource,
        destination: Path,
    ) -> tuple[str, int]:
        """Copy one file's bytes from the source into a local destination path.

        Args:
            article_id: The article the file belongs to.
            round_label: The round folder the file belongs to.
            relative_path: The file's path relative to its round folder.
            source: The batch source it belongs to.
            destination: The local path to write the bytes to. The parent
                directory is assumed to already exist.

        Returns:
            A ``(checksum, bytes_transferred)`` tuple — the SHA-256
            checksum computed as bytes were streamed, and the total byte
            count written.

        Raises:
            SourceUnavailableError: If the specific file does not exist
                or cannot be accessed.
            S3ReadTransientError: If an S3-backed reader encounters a
                transient API failure (throttling, timeout) while the
                object does exist.
        """
