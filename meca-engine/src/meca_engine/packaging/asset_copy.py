"""Asset Copy Engine — Package Assembly (Milestone 7).

Copies every physical file manifest.xml declares from its staged
location into the package's ``files/<round_label>/...`` tree. Contains
no business logic: it never decides *which* files belong in the package
(that decision was already made by manifest.xml — see
:mod:`meca_engine.packaging.document_reader`) — only *how* to copy them
safely.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from meca_engine.exceptions.article_errors import PackageAssemblyError
from meca_engine.packaging.models import AssetCopyReport
from meca_engine.utils.hashing import compute_stream_checksum_while_copying

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.logging_.structured_logger import StructuredLogger
    from meca_engine.packaging.models import PackagedFile

_STAGE = "meca_engine.packaging.asset_copy"


class AssetCopyService:
    """Streams staged files into a package's ``files/`` tree, verifying as it goes.

    Never buffers a whole file in memory (13_LLD_04 §9.3): copying and
    checksum verification happen in one streamed pass via
    :func:`meca_engine.utils.hashing.compute_stream_checksum_while_copying`.
    """

    def __init__(self, *, overwrite_policy: str, logger: StructuredLogger) -> None:
        """Initialize the copy service.

        Args:
            overwrite_policy: One of ``"fail"``, ``"overwrite"``, or
                ``"skip"`` — behavior when a destination file already
                exists (:class:`meca_engine.config.schema.PackagingSettings`).
            logger: The structured logger to emit ``asset copied`` events to.
        """
        self._overwrite_policy = overwrite_policy
        self._logger = logger

    def copy_all(
        self, entries: tuple[PackagedFile, ...], *, destination_root: Path, article_id: str
    ) -> AssetCopyReport:
        """Copy every entry's source file to ``destination_root / entry.href``.

        Args:
            entries: The manifest-derived copy plan (already deduplicated
                against ``destination_root`` by the caller having built
                one entry per distinct href).
            destination_root: The package staging directory's root; each
                entry's ``href`` (e.g. ``"files/R1/figure1.jpg"``) is
                joined onto this to form the destination path, so the
                round subfolder hierarchy is created automatically.
            article_id: For logging/error context only.

        Returns:
            A report of every file copied, skipped, or found duplicated.

        Raises:
            PackageAssemblyError: If a source file is missing (permanent,
                not retryable), a destination collision occurs under
                ``overwrite_policy="fail"`` (permanent), or a post-copy
                checksum/size mismatch is detected (retryable — most
                often transient disk-level corruption, mirroring
                :class:`meca_engine.exceptions.article_errors.StagingIntegrityError`'s
                own reasoning).
        """
        seen_hrefs: set[str] = set()
        duplicate_hrefs: list[str] = []
        copied: list[PackagedFile] = []
        skipped: list[PackagedFile] = []

        for entry in entries:
            if entry.href in seen_hrefs:
                duplicate_hrefs.append(entry.href)
                continue
            seen_hrefs.add(entry.href)

            if not entry.source_path.is_file():
                raise PackageAssemblyError(
                    f"Missing staged asset for href {entry.href!r}: {entry.source_path}",
                    retryable=False,
                    article_id=article_id,
                    stage=_STAGE,
                    rule_id="BR-152",
                )

            destination_path = destination_root / entry.href
            if destination_path.exists():
                if self._overwrite_policy == "fail":
                    raise PackageAssemblyError(
                        f"Destination already exists for href {entry.href!r}: {destination_path}",
                        retryable=False,
                        article_id=article_id,
                        stage=_STAGE,
                    )
                if self._overwrite_policy == "skip":
                    skipped.append(entry)
                    continue

            self._copy_one(entry, destination_path, article_id=article_id)
            copied.append(entry)

        return AssetCopyReport(
            copied=tuple(copied),
            skipped=tuple(skipped),
            duplicate_hrefs=tuple(duplicate_hrefs),
        )

    def _copy_one(self, entry: PackagedFile, destination_path: Path, *, article_id: str) -> None:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        with entry.source_path.open("rb") as source, destination_path.open("wb") as destination:
            checksum, bytes_transferred = compute_stream_checksum_while_copying(source, destination)

        if checksum != entry.checksum or bytes_transferred != entry.size_bytes:
            destination_path.unlink(missing_ok=True)
            raise PackageAssemblyError(
                f"Post-copy integrity check failed for href {entry.href!r}: "
                f"expected checksum={entry.checksum!r} size={entry.size_bytes}, "
                f"got checksum={checksum!r} size={bytes_transferred}",
                retryable=True,
                article_id=article_id,
                stage=_STAGE,
            )

        shutil.copystat(entry.source_path, destination_path)
        self._logger.info(
            "asset copied",
            stage=_STAGE,
            context={"article_id": article_id, "href": entry.href, "size_bytes": entry.size_bytes},
        )
