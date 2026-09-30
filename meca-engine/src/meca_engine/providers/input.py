"""Input Provider — Archive Migration Platform Phase 1 (ADR-030).

Defines where the batch pipeline reads its articles from. Reproduces
today's exact behavior (a local directory of ``<ArticleID>.zip``
archives) behind an interface a future S3-backed deployment can
implement without touching anything downstream of :class:`StagedArticle`.
"""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from meca_engine.exceptions import (
    InvalidArticlePackageError,
    ProviderNotConfiguredError,
    SourceUnavailableError,
)

if TYPE_CHECKING:
    from meca_engine.config.schema import InputSettings

_STAGE = "meca_engine.providers.input"


@dataclass(frozen=True)
class StagedArticle:
    """One article, extracted and ready for the existing pipeline to read.

    Attributes:
        article_id: The article's identifier (its archive's filename, minus ``.zip``).
        staged_root: The local directory containing the article's round
            folders — exactly what :mod:`meca_engine.extraction.file_resolver`
            already expects as ``staged_root``.
        source_xml_path: The discovered root source XML file.
        extraction_root: The temporary directory this article was
            extracted into, if any (``None`` for a provider that stages
            from an already-persistent location). Distinct from
            ``staged_root`` — which may be a nested subdirectory of
            it — so a caller can remove the *entire* extraction, not
            just the part :mod:`~meca_engine.extraction.file_resolver`
            reads from. The caller (:class:`~meca_engine.service.worker.Worker`)
            removes this once the article is fully processed, matching
            13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md §9.4's existing
            "working directory deleted after success or terminal
            failure" lifecycle.
    """

    article_id: str
    staged_root: Path
    source_xml_path: Path
    extraction_root: Path | None = None


class InputProvider(ABC):
    """Where the batch reads its articles from."""

    @abstractmethod
    def list_articles(self) -> tuple[str, ...]:
        """List every article id available to process, in a stable order."""

    @abstractmethod
    def stage_article(self, article_id: str) -> StagedArticle:
        """Make one article's content available on local disk for the existing pipeline."""


class LocalInputProvider(InputProvider):
    """Reads ``<ArticleID>.zip`` archives from a local directory.

    Extraction happens here (not in a shared reader) specifically so the
    rest of the pipeline — everything from :class:`~meca_engine.extraction.xml_loader.XmlLoader`
    onward — behaves exactly as it does today; see the module docstring
    for why this does not reuse :class:`~meca_engine.input.readers.local_reader.LocalFolderReader`.
    """

    def __init__(self, local_path: str) -> None:
        """Initialize the provider.

        Args:
            local_path: Directory containing one ``<ArticleID>.zip`` per article.
        """
        self._root = Path(local_path)

    def list_articles(self) -> tuple[str, ...]:
        """List every ``.zip`` archive's stem under ``local_path``, sorted for determinism."""
        return tuple(sorted(p.stem for p in self._root.glob("*.zip")))

    def stage_article(self, article_id: str) -> StagedArticle:
        """Extract ``<article_id>.zip`` to a fresh temp directory and locate its source XML.

        Raises:
            SourceUnavailableError: The archive does not exist, or is not a
                readable ZIP (empty/corrupt) — a source-data problem, not
                an engine defect.
            InvalidArticlePackageError: The archive is a readable ZIP but
                contains no source XML file at all, or contains a member
                path that would extract outside the staging directory
                ("zip slip") — a corrupt/malicious archive, never a
                genuine publisher submission.
        """
        zip_path = self._root / f"{article_id}.zip"
        tmp_path = Path(tempfile.mkdtemp(prefix=f"am_{article_id}_"))
        try:
            try:
                with zipfile.ZipFile(zip_path) as archive:
                    names = [n for n in archive.namelist() if "__MACOSX" not in n]
                    _reject_unsafe_members(names, tmp_path, article_id)
                    archive.extractall(tmp_path, members=names)
            except FileNotFoundError as exc:
                raise SourceUnavailableError(
                    f"Source archive not found for {article_id!r}: {zip_path}",
                    article_id=article_id,
                    stage=_STAGE,
                    inner_cause=exc,
                ) from exc
            except zipfile.BadZipFile as exc:
                raise SourceUnavailableError(
                    f"Source archive for {article_id!r} is corrupt or not a valid ZIP: {exc}",
                    article_id=article_id,
                    stage=_STAGE,
                    inner_cause=exc,
                ) from exc
            source_xml_path = _find_source_xml(tmp_path, article_id)
        except BaseException:
            # Never leave a partial/unusable extraction behind on disk —
            # mirrors 13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md §9.4's
            # existing "working directory removed on terminal failure"
            # lifecycle (see the module-level `Stager.cleanup()` in
            # `input/staging.py`, this provider's own predecessor).
            shutil.rmtree(tmp_path, ignore_errors=True)
            raise
        return StagedArticle(
            article_id=article_id,
            staged_root=source_xml_path.parent,
            source_xml_path=source_xml_path,
            extraction_root=tmp_path,
        )


def _reject_unsafe_members(names: list[str], destination_root: Path, article_id: str) -> None:
    """Reject a ZIP outright if any member would extract outside ``destination_root``.

    RC-1 security review: :meth:`zipfile.ZipFile.extractall` does not
    protect against "zip slip" — a member name such as
    ``"../../../etc/cron.d/evil"`` or an absolute path is not sanitized by
    the stdlib and could otherwise write outside the intended staging
    directory. Checked once, before extraction, against every member
    name; a single unsafe member fails the whole archive rather than
    silently skipping just that one entry, since a crafted path is a sign
    the archive itself should not be trusted.
    """
    destination_root = destination_root.resolve()
    for name in names:
        resolved = (destination_root / name).resolve()
        if resolved != destination_root and destination_root not in resolved.parents:
            raise InvalidArticlePackageError(
                f"Source archive for {article_id!r} contains an unsafe member "
                f"path outside the staging directory: {name!r}",
                article_id=article_id,
                stage=_STAGE,
            )


class S3InputProvider(InputProvider):
    """Placeholder — AWS S3 input is not implemented in Phase 1 (ADR-030)."""

    def list_articles(self) -> tuple[str, ...]:
        """Not implemented.

        See :class:`~meca_engine.exceptions.batch_errors.ProviderNotConfiguredError`.
        """
        raise ProviderNotConfiguredError(
            "S3InputProvider is not implemented (Archive Migration Platform, future phase).",
            stage=_STAGE,
        )

    def stage_article(self, article_id: str) -> StagedArticle:
        """Not implemented.

        See :class:`~meca_engine.exceptions.batch_errors.ProviderNotConfiguredError`.
        """
        raise ProviderNotConfiguredError(
            "S3InputProvider is not implemented (Archive Migration Platform, future phase).",
            stage=_STAGE,
            article_id=article_id,
        )


def create_input_provider(settings: InputSettings) -> InputProvider:
    """Provider Factory: select an :class:`InputProvider` from configuration.

    Raises:
        ProviderNotConfiguredError: If ``settings.provider`` names a
            provider this phase does not recognize at all (schema
            validation already rejects anything outside ``LOCAL``/``S3``,
            so this is defense-in-depth, not a reachable production path).
    """
    if settings.provider == "LOCAL":
        return LocalInputProvider(settings.local_path)
    if settings.provider == "S3":
        return S3InputProvider()
    raise ProviderNotConfiguredError(f"Unknown input provider: {settings.provider!r}", stage=_STAGE)


def _find_source_xml(extracted_root: Path, article_id: str) -> Path:
    candidates = [
        p
        for p in extracted_root.rglob("*.xml")
        if "__MACOSX" not in p.parts and not p.name.startswith("._")
    ]
    if not candidates:
        raise InvalidArticlePackageError(
            f"No source XML found for {article_id!r} under {extracted_root}",
            article_id=article_id,
            stage=_STAGE,
        )
    if len(candidates) == 1:
        return candidates[0]
    for p in candidates:
        if p.stem.lower() == article_id.lower():
            return p
    return candidates[0]
