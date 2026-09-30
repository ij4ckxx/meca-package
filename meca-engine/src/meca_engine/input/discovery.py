"""Article & Batch Discovery.

Scans a batch source and produces validated
:class:`~meca_engine.input.models.ArticleReference` objects — structural
validation only (BR-001's "exactly one root-level XML file" and BR-002's
"at least one round folder" existence/count checks), never XML content
parsing. One bad article never prevents the rest of the batch from being
discovered (ADR-009's "isolate failures per article" principle) — a
structurally invalid article is recorded as a
:class:`~meca_engine.input.models.DiscoveryFailure` and the scan continues.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from meca_engine.exceptions import (
    DuplicateFileError,
    InvalidArticlePackageError,
    SourceUnavailableError,
)
from meca_engine.input.models import (
    ArticleReference,
    Batch,
    BatchSource,
    DiscoveryFailure,
    FileInventory,
    FileRecord,
)

if TYPE_CHECKING:
    from meca_engine.input.readers.base import InputReader
    from meca_engine.logging_ import StructuredLogger

_STAGE = "meca_engine.input.discovery"

# Purely technical/hygiene anomaly markers — NOT the business-rule-driven
# "which files belong to the submission" determination (that remains
# Milestone 3's Metadata Extractor / File Resolver responsibility, driven
# by the source XML's custom-meta, per Business Rule Book BR-011/BR-014).
_KNOWN_OS_ARTIFACT_FILENAMES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})


class BatchDiscovery:
    """Scans a batch source and produces a :class:`~meca_engine.input.models.Batch`."""

    def __init__(self, reader: InputReader, logger: StructuredLogger) -> None:
        """Initialize the discovery scanner.

        Args:
            reader: The :class:`~meca_engine.input.readers.base.InputReader`
                to enumerate the source through.
            logger: The structured logger to emit discovery events through.
        """
        self._reader = reader
        self._logger = logger

    def discover(self, source: BatchSource, *, batch_id: str) -> Batch:
        """Scan a batch source and return every discoverable article reference.

        Args:
            source: The batch source to scan.
            batch_id: A human-readable identifier for this scan, used for
                logging/correlation only.

        Returns:
            A :class:`~meca_engine.input.models.Batch` containing every
            structurally-valid article as an
            :class:`~meca_engine.input.models.ArticleReference`, plus a
            :class:`~meca_engine.input.models.DiscoveryFailure` for every
            article that failed structural validation.

        Raises:
            SourceUnavailableError: If the batch root itself cannot be
                listed at all (there is no batch to report on in that case).
        """
        self._logger.info("Batch discovery starting", stage=_STAGE, context={"batch_id": batch_id})
        candidate_ids = self._reader.list_batch_article_ids(source)

        seen_ids: set[str] = set()
        article_refs: list[ArticleReference] = []
        failures: list[DiscoveryFailure] = []

        for article_id in candidate_ids:
            if article_id in seen_ids:
                reason = f"duplicate article_id encountered during batch scan: {article_id!r}"
                self._logger.warn(reason, stage=_STAGE, context={"article_id": article_id})
                failures.append(
                    DiscoveryFailure(
                        article_id=article_id,
                        reason=reason,
                        exception_type="DuplicateArticleError",
                    )
                )
                continue
            seen_ids.add(article_id)

            try:
                article_ref = self._discover_one(article_id, source)
            except (InvalidArticlePackageError, DuplicateFileError, SourceUnavailableError) as exc:
                self._logger.log_exception(exc)
                failures.append(
                    DiscoveryFailure(
                        article_id=article_id,
                        reason=exc.message,
                        exception_type=type(exc).__name__,
                    )
                )
                continue

            article_refs.append(article_ref)
            self._logger.info(
                "Article discovered",
                stage=_STAGE,
                context={
                    "article_id": article_id,
                    "round_labels": list(article_ref.file_inventory.round_labels),
                    "file_count": len(article_ref.file_inventory.files),
                },
            )

        discovered_at = datetime.now(timezone.utc)
        self._logger.audit(
            "Batch discovery completed",
            stage=_STAGE,
            context={
                "batch_id": batch_id,
                "discovered": len(article_refs),
                "failed": len(failures),
            },
        )
        return Batch(
            batch_id=batch_id,
            source=source,
            article_refs=tuple(article_refs),
            discovery_failures=tuple(failures),
            discovered_at=discovered_at,
        )

    def _discover_one(self, article_id: str, source: BatchSource) -> ArticleReference:
        top_level = self._reader.list_article_top_level(article_id, source)

        xml_candidates = tuple(
            entry.name
            for entry in top_level
            if not entry.is_directory and entry.name.lower().endswith(".xml")
        )
        round_labels = tuple(entry.name for entry in top_level if entry.is_directory)

        if len(xml_candidates) != 1:
            raise InvalidArticlePackageError(
                f"Expected exactly one root-level .xml file, found "
                f"{len(xml_candidates)}: {list(xml_candidates)}",
                article_id=article_id,
                stage=_STAGE,
                rule_id="BR-001",
            )
        if not round_labels:
            raise InvalidArticlePackageError(
                "No submission-round folder found under the article root",
                article_id=article_id,
                stage=_STAGE,
                rule_id="BR-002",
            )

        all_files: list[FileRecord] = []
        anomalous_paths: list[str] = []
        seen_within_round: set[tuple[str, str]] = set()

        for round_label in round_labels:
            for file_record in self._reader.list_round_files(article_id, round_label, source):
                dedup_key = (round_label, file_record.relative_path.lower())
                if dedup_key in seen_within_round:
                    raise DuplicateFileError(
                        f"Duplicate filename within round {round_label!r}: "
                        f"{file_record.relative_path!r}",
                        article_id=article_id,
                        stage=_STAGE,
                    )
                seen_within_round.add(dedup_key)

                basename = PurePosixPath(file_record.relative_path).name
                if file_record.size_bytes == 0 or basename in _KNOWN_OS_ARTIFACT_FILENAMES:
                    anomalous_paths.append(f"{round_label}/{file_record.relative_path}")

                all_files.append(file_record)

        inventory = FileInventory(
            files=tuple(all_files),
            anomalous_relative_paths=tuple(anomalous_paths),
        )
        return ArticleReference(
            article_id=article_id,
            source=source,
            root_xml_relative_name=xml_candidates[0],
            file_inventory=inventory,
            discovered_at=datetime.now(timezone.utc),
        )
