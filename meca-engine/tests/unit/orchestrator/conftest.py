"""Shared fixtures for orchestrator unit tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from meca_engine.input.models import ArticleReference, FileInventory, LocalBatchSource

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def make_article_reference() -> Callable[[str], ArticleReference]:
    """Return a factory building a minimal, valid ArticleReference for a given id."""

    def _make(article_id: str) -> ArticleReference:
        return ArticleReference(
            article_id=article_id,
            source=LocalBatchSource(root_path=Path("/tmp/batch")),
            root_xml_relative_name=f"{article_id}.xml",
            file_inventory=FileInventory(),
            discovered_at=datetime.now(timezone.utc),
        )

    return _make
