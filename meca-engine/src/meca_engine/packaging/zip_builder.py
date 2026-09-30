"""ZIP Builder — Package Assembly (Milestone 7).

Produces the final ``MECA_<ArticleID>.zip``. Deterministic (files added
in a fixed, sorted order) and reproducible (a fixed archive-entry
timestamp, independent of the real filesystem mtimes of the staged
files) so that re-running assembly against unchanged input produces a
byte-identical zip — useful for batch reruns and for detecting
unintended drift. Streams every file's bytes directly from disk into
the archive (13_LLD_04 §9.3: "binary attachments are never read into
process memory"); never holds a whole file's bytes in a Python object.
"""

from __future__ import annotations

import shutil
import zipfile
from typing import TYPE_CHECKING

from meca_engine.exceptions.article_errors import PackageAssemblyError

if TYPE_CHECKING:
    from pathlib import Path

    from meca_engine.logging_.structured_logger import StructuredLogger

_STAGE = "meca_engine.packaging.zip_builder"
_COPY_CHUNK_SIZE = 1024 * 1024  # 1 MiB
_FIXED_ARCHIVE_DATE_TIME = (1980, 1, 1, 0, 0, 0)  # zip format epoch — reproducible output

_COMPRESSION_BY_NAME = {
    "deflated": zipfile.ZIP_DEFLATED,
    "stored": zipfile.ZIP_STORED,
}


class ZipBuilder:
    """Assembles a directory tree into a deterministic, streamed zip archive."""

    def __init__(
        self, *, compression: str, compresslevel: int | None, logger: StructuredLogger
    ) -> None:
        """Initialize the zip builder.

        Args:
            compression: ``"deflated"`` or ``"stored"``
                (:class:`meca_engine.config.schema.PackagingSettings`).
            compresslevel: Passed through to ``zipfile.ZipFile`` when
                ``compression`` is ``"deflated"``; ``None`` uses the
                zipfile module's own default.
            logger: The structured logger to emit ``zip completed`` to.

        Raises:
            PackageAssemblyError: If ``compression`` is not a recognized name.
        """
        if compression not in _COMPRESSION_BY_NAME:
            raise PackageAssemblyError(
                f"Unrecognized zip_compression {compression!r}; expected one of "
                f"{sorted(_COMPRESSION_BY_NAME)}",
                retryable=False,
                stage=_STAGE,
            )
        self._compression = _COMPRESSION_BY_NAME[compression]
        self._compresslevel = compresslevel
        self._logger = logger

    def build(self, *, source_root: Path, zip_path: Path, article_id: str) -> None:
        """Zip every file under ``source_root`` into ``zip_path``.

        Args:
            source_root: The package staging directory (its own name is
                never included in archive entry paths — only paths
                relative to it).
            zip_path: Where to write the final archive. Its parent
                directory is created if missing.
            article_id: For logging context only.
        """
        file_paths = sorted(
            (path for path in source_root.rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(source_root).as_posix(),
        )
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(
            zip_path,
            mode="w",
            compression=self._compression,
            compresslevel=self._compresslevel,
        ) as archive:
            for file_path in file_paths:
                arcname = file_path.relative_to(source_root).as_posix()
                info = zipfile.ZipInfo(arcname, date_time=_FIXED_ARCHIVE_DATE_TIME)
                info.compress_type = self._compression
                with file_path.open("rb") as source, archive.open(info, mode="w") as destination:
                    shutil.copyfileobj(source, destination, length=_COPY_CHUNK_SIZE)

        self._logger.info(
            "zip completed",
            stage=_STAGE,
            context={
                "article_id": article_id,
                "zip_path": str(zip_path),
                "file_count": len(file_paths),
            },
        )
