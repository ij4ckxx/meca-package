"""Working-directory staging: copy/download, integrity verification, cleanup.

Per 13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md §9.4: each article gets
its own working subdirectory, deleted after either a successful publish
or a terminal failure — never left behind as a side effect of either
outcome. Disk-space is treated as a batch-level concern (§9.4's own
reasoning, quoted in
:class:`~meca_engine.exceptions.InsufficientDiskSpaceError`'s docstring),
not a per-article one.
"""

from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from meca_engine.exceptions import InsufficientDiskSpaceError, StagingIntegrityError
from meca_engine.input.models import ArticleReference, FileInventory, StagedArticle
from meca_engine.logging_ import PerformanceTimer, StructuredLogger
from meca_engine.utils.hashing import compute_file_checksum

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.input.readers.base import InputReader

_STAGE = "meca_engine.input.staging"

_DEFAULT_DISK_SPACE_MARGIN = 0.1  # require 10% headroom beyond an article's own size


class Stager:
    """Copies/downloads one article's files into a local working directory.

    Attributes:
        reader: The :class:`~meca_engine.input.readers.base.InputReader`
            used to fetch file bytes.
        working_dir_root: The root directory every run's working
            directories are created under.
        run_id: A human-readable identifier scoping this ``Stager``
            instance's working directories to one run, avoiding collision
            with a previous or concurrent run's leftover directories.
    """

    def __init__(
        self,
        reader: InputReader,
        working_dir_root: Path,
        logger: StructuredLogger,
        *,
        run_id: str | None = None,
        disk_space_margin: float = _DEFAULT_DISK_SPACE_MARGIN,
    ) -> None:
        """Initialize the stager.

        Args:
            reader: The input reader to fetch file bytes through.
            working_dir_root: Root directory for this run's working
                directories (13_LLD_04... §9.4, ADR-020).
            logger: The structured logger to emit staging events through.
            run_id: A unique id scoping this run's working directories;
                auto-generated if not supplied.
            disk_space_margin: Fractional headroom required beyond an
                article's total file size before staging is allowed to
                proceed (e.g. ``0.1`` = require 10% extra free space).
                The exact production threshold is an open engineering
                question (16_LLD_07_READINESS_ASSESSMENT.md §15.2 TQ-06);
                this default is a reasonable, documented placeholder.
        """
        self.reader = reader
        self.working_dir_root = working_dir_root
        self.run_id = run_id or uuid.uuid4().hex
        self._logger = logger
        self._disk_space_margin = disk_space_margin

    def stage_article(self, article_ref: ArticleReference) -> StagedArticle:
        """Copy/download every file in an article's inventory into a fresh working directory.

        Args:
            article_ref: The article to stage, as produced by
                :class:`~meca_engine.input.discovery.BatchDiscovery`.

        Returns:
            A :class:`~meca_engine.input.models.StagedArticle` with every
            file's checksum and local path populated.

        Raises:
            InsufficientDiskSpaceError: If available disk space is
                insufficient to safely stage this article.
            StagingIntegrityError: If a copied/downloaded file's size or
                checksum does not match expectations.
            SourceUnavailableError: If a referenced file cannot be
                fetched from the source at all.

        On any failure, the partially-created working directory is
        removed before the exception propagates (safe cleanup) — a
        partially-staged article is never left on disk to be mistaken
        for a complete one.
        """
        working_directory = self._create_workspace(article_ref.article_id)
        with PerformanceTimer(self._logger, _STAGE, context={"article_id": article_ref.article_id}):
            try:
                self._validate_disk_space(article_ref, working_directory)
                staged_records = []
                for file_record in article_ref.file_inventory.files:
                    destination = (
                        working_directory / file_record.round_label / file_record.relative_path
                    )
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    checksum, bytes_transferred = self.reader.fetch_file(
                        article_ref.article_id,
                        file_record.round_label,
                        file_record.relative_path,
                        article_ref.source,
                        destination,
                    )
                    self._verify_integrity(
                        article_ref.article_id,
                        file_record.relative_path,
                        expected_size=file_record.size_bytes,
                        actual_size=bytes_transferred,
                        transfer_checksum=checksum,
                        destination=destination,
                    )
                    staged_records.append(
                        file_record.with_staging_result(
                            checksum=checksum, staged_local_path=destination
                        )
                    )
            except BaseException:
                self.cleanup(working_directory)
                raise

        staged_article = StagedArticle(
            article_id=article_ref.article_id,
            working_directory=working_directory,
            source=article_ref.source,
            file_inventory=FileInventory(
                files=tuple(staged_records),
                anomalous_relative_paths=article_ref.file_inventory.anomalous_relative_paths,
            ),
            staged_at=datetime.now(timezone.utc),
        )
        self._logger.info(
            "Article staged successfully",
            stage=_STAGE,
            context={
                "article_id": article_ref.article_id,
                "file_count": len(staged_records),
                "total_bytes": staged_article.file_inventory.total_size_bytes,
            },
        )
        return staged_article

    def cleanup(self, working_directory: Path) -> None:
        """Safely remove a working directory and everything under it.

        Never raises — a cleanup failure must never mask the original
        error that triggered it, nor crash an otherwise-successful
        publish path that calls this afterward.

        Args:
            working_directory: The directory to remove.
        """
        shutil.rmtree(working_directory, ignore_errors=True)
        self._logger.info(
            "Workspace cleaned up",
            stage=_STAGE,
            context={"working_directory": str(working_directory)},
        )

    def _create_workspace(self, article_id: str) -> Path:
        working_directory = self.working_dir_root / self.run_id / article_id
        working_directory.mkdir(parents=True, exist_ok=True)
        return working_directory

    def _validate_disk_space(self, article_ref: ArticleReference, working_directory: Path) -> None:
        required_bytes = article_ref.file_inventory.total_size_bytes
        usage = shutil.disk_usage(working_directory)
        required_with_margin = int(required_bytes * (1 + self._disk_space_margin))
        if usage.free < required_with_margin:
            raise InsufficientDiskSpaceError(
                f"Insufficient disk space to stage article {article_ref.article_id!r}: "
                f"need ~{required_with_margin} bytes ({required_bytes} + "
                f"{self._disk_space_margin:.0%} margin), only {usage.free} bytes free "
                f"at {working_directory}",
                article_id=article_ref.article_id,
                stage=_STAGE,
            )

    def _verify_integrity(
        self,
        article_id: str,
        relative_path: str,
        *,
        expected_size: int,
        actual_size: int,
        transfer_checksum: str,
        destination: Path,
    ) -> None:
        if actual_size != expected_size:
            raise StagingIntegrityError(
                f"Size mismatch staging {relative_path!r}: expected {expected_size} "
                f"bytes, transferred {actual_size} bytes",
                article_id=article_id,
                stage=_STAGE,
            )
        on_disk_checksum = compute_file_checksum(destination)
        if on_disk_checksum != transfer_checksum:
            raise StagingIntegrityError(
                f"Checksum mismatch staging {relative_path!r}: as-transferred "
                f"{transfer_checksum}, as-read-back {on_disk_checksum}",
                article_id=article_id,
                stage=_STAGE,
            )
