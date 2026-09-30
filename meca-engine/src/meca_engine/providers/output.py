"""Output Provider — Archive Migration Platform Phase 1 (ADR-030).

Defines where the batch pipeline writes its generated packages.
Reproduces today's exact behavior (a local directory, one subfolder per
article) behind an interface a future SFTP-backed deployment can
implement without touching :class:`~meca_engine.packaging.builder.PackageBuilder`.

Deliberately never defaults to ``./Output`` — see
:class:`~meca_engine.config.schema.OutputSettings`'s docstring and the
Phase 1 Configuration Guide.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from meca_engine.exceptions import ProviderNotConfiguredError

if TYPE_CHECKING:
    from meca_engine.config.schema import OutputSettings

_STAGE = "meca_engine.providers.output"


class OutputProvider(ABC):
    """Where the batch writes its generated packages and per-article reports."""

    @abstractmethod
    def article_output_root(self, article_id: str) -> Path:
        """Return this article's output directory, creating it if needed."""

    @abstractmethod
    def category_root(self, category: str) -> Path:
        """Return a named output category's root directory, creating it if needed.

        Added for the Automated Migration Service (Phase 3, ADR-031):
        decision-routed destinations (``uploaded``, ``manual_review``,
        ``failed``) that are siblings of the per-article staging root
        :meth:`article_output_root` writes into, not subdirectories of it.

        Args:
            category: The category name (e.g. ``"uploaded"``).
        """


class LocalOutputProvider(OutputProvider):
    """Writes generated packages under a local directory, one subfolder per article."""

    def __init__(self, local_path: str) -> None:
        """Initialize the provider.

        Args:
            local_path: Root directory generated packages are written under.
        """
        self._root = Path(local_path)
        self._root.mkdir(parents=True, exist_ok=True)

    def article_output_root(self, article_id: str) -> Path:
        """Return (creating if needed) ``<local_path>/<article_id>/``."""
        path = self._root / article_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def category_root(self, category: str) -> Path:
        """Return (creating if needed) ``<local_path>/<category>/``."""
        path = self._root / category
        path.mkdir(parents=True, exist_ok=True)
        return path


class SftpOutputProvider(OutputProvider):
    """Placeholder — SFTP output is not implemented in Phase 1 (ADR-030)."""

    def article_output_root(self, article_id: str) -> Path:
        """Not implemented.

        See :class:`~meca_engine.exceptions.batch_errors.ProviderNotConfiguredError`.
        """
        raise ProviderNotConfiguredError(
            "SftpOutputProvider is not implemented (Archive Migration Platform, future phase).",
            stage=_STAGE,
            article_id=article_id,
        )

    def category_root(self, category: str) -> Path:
        """Not implemented.

        See :class:`~meca_engine.exceptions.batch_errors.ProviderNotConfiguredError`.
        """
        raise ProviderNotConfiguredError(
            "SftpOutputProvider is not implemented (Archive Migration Platform, future phase).",
            stage=_STAGE,
        )


def create_output_provider(settings: OutputSettings) -> OutputProvider:
    """Provider Factory: select an :class:`OutputProvider` from configuration.

    Raises:
        ProviderNotConfiguredError: If ``settings.provider`` names a
            provider this phase does not recognize at all (schema
            validation already rejects anything outside
            ``LOCAL``/``S3``/``SFTP``, so this is defense-in-depth).
    """
    if settings.provider == "LOCAL":
        return LocalOutputProvider(settings.local_path)
    if settings.provider == "SFTP":
        return SftpOutputProvider()
    raise ProviderNotConfiguredError(
        f"Unknown output provider: {settings.provider!r}", stage=_STAGE
    )
