"""Local Folder Reader.

Reads a batch of articles laid out as ``<root>/<ArticleID>/<Round>/<file>``
on local disk — the shape observed directly in the Reverse Engineering
Report's 3 real sample inputs. Primarily intended for local development
and testing (see ``README.md``'s "Local Setup"); production input is S3
(ADR-019), served by :class:`~meca_engine.input.readers.s3_reader.S3Reader`.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from meca_engine.exceptions import SourceUnavailableError
from meca_engine.input.models import BatchSource, FileRecord, LocalBatchSource
from meca_engine.input.readers.base import InputReader, TopLevelEntry
from meca_engine.utils.hashing import compute_stream_checksum_while_copying

if TYPE_CHECKING:
    from pathlib import Path

_STAGE = "meca_engine.input.readers.local_reader"


def _require_local_source(source: BatchSource) -> LocalBatchSource:
    if not isinstance(source, LocalBatchSource):
        raise TypeError(
            f"LocalFolderReader requires a LocalBatchSource, got {type(source).__name__}"
        )
    return source


class LocalFolderReader(InputReader):
    """Reads batches of articles from a local directory tree."""

    def list_batch_article_ids(self, source: BatchSource) -> tuple[str, ...]:
        """List every article subfolder directly under the batch root.

        Args:
            source: Must be a :class:`~meca_engine.input.models.LocalBatchSource`.

        Returns:
            Article folder names, sorted for deterministic ordering.

        Raises:
            SourceUnavailableError: If the batch root does not exist or
                is not a directory.
        """
        local_source = _require_local_source(source)
        root = local_source.root_path
        if not root.is_dir():
            raise SourceUnavailableError(
                f"Batch root does not exist or is not a directory: {root}",
                stage=_STAGE,
            )
        with os.scandir(root) as entries:
            names = sorted(entry.name for entry in entries if entry.is_dir())
        return tuple(names)

    def list_article_top_level(
        self, article_id: str, source: BatchSource
    ) -> tuple[TopLevelEntry, ...]:
        """List the entries directly under one article's own folder."""
        local_source = _require_local_source(source)
        article_root = local_source.root_path / article_id
        if not article_root.is_dir():
            raise SourceUnavailableError(
                f"Article root does not exist or is not a directory: {article_root}",
                article_id=article_id,
                stage=_STAGE,
            )
        with os.scandir(article_root) as entries:
            result = sorted(
                (TopLevelEntry(name=entry.name, is_directory=entry.is_dir()) for entry in entries),
                key=lambda item: item.name,
            )
        return tuple(result)

    def list_round_files(
        self, article_id: str, round_label: str, source: BatchSource
    ) -> tuple[FileRecord, ...]:
        """List every file under one article's one round folder, recursively."""
        local_source = _require_local_source(source)
        round_root = local_source.root_path / article_id / round_label
        if not round_root.is_dir():
            raise SourceUnavailableError(
                f"Round folder does not exist or is not a directory: {round_root}",
                article_id=article_id,
                stage=_STAGE,
            )
        records: list[FileRecord] = []
        for path in sorted(round_root.rglob("*")):
            if not path.is_file():
                continue
            relative_path = path.relative_to(round_root).as_posix()
            records.append(
                FileRecord(
                    round_label=round_label,
                    relative_path=relative_path,
                    size_bytes=path.stat().st_size,
                )
            )
        return tuple(records)

    def fetch_file(
        self,
        article_id: str,
        round_label: str,
        relative_path: str,
        source: BatchSource,
        destination: Path,
    ) -> tuple[str, int]:
        """Copy one file's bytes from the local source into a destination path."""
        local_source = _require_local_source(source)
        source_path = local_source.root_path / article_id / round_label / relative_path
        try:
            with source_path.open("rb") as source_stream, destination.open("wb") as dest_stream:
                return compute_stream_checksum_while_copying(source_stream, dest_stream)
        except OSError as exc:
            raise SourceUnavailableError(
                f"Could not read source file: {source_path}",
                article_id=article_id,
                stage=_STAGE,
                inner_cause=exc,
            ) from exc
