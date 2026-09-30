"""Shared pytest fixtures for the whole test suite.

Per 14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md §13.6: only truly global
fixtures live here; package-specific fixtures belong in a ``conftest.py`` at
the appropriate narrower scope.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from meca_engine.logging_.correlation import reset_context

if TYPE_CHECKING:
    from collections.abc import Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def repo_root() -> Path:
    """Return the repository root directory."""
    return REPO_ROOT


@pytest.fixture
def schema_dir(repo_root: Path) -> Path:
    """Return the real ``schemas/config-schema`` directory shipped with the app."""
    return repo_root / "schemas" / "config-schema"


@pytest.fixture
def valid_config_dir(repo_root: Path) -> Path:
    """Return the fixture configuration directory used by config unit tests."""
    return repo_root / "tests" / "fixtures" / "config"


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


@pytest.fixture
def valid_batch_root(tmp_path: Path) -> Path:
    """Build a local batch root with 2 structurally-valid, multi-round articles.

    Shared across the Input & Staging Layer tests (``tests/unit/input/``)
    and the Orchestrator tests (``tests/unit/orchestrator/``), both of
    which need a realistic, valid local batch to run a full
    discover-then-stage flow against.
    """
    root = tmp_path / "batch"

    # Article 1: two rounds, a manuscript in each.
    _write_bytes(root / "ART-0001" / "ART-0001.xml", b"<article/>")
    _write_bytes(root / "ART-0001" / "Original" / "manuscript.txt", b"original manuscript content")
    _write_bytes(root / "ART-0001" / "Original" / "fig1.txt", b"figure one content")
    _write_bytes(root / "ART-0001" / "R1" / "manuscript.txt", b"revised manuscript content")

    # Article 2: single round.
    _write_bytes(root / "ART-0002" / "ART-0002.xml", b"<article/>")
    _write_bytes(root / "ART-0002" / "Original" / "manuscript.txt", b"another manuscript")

    return root


@pytest.fixture(autouse=True)
def _reset_correlation_context() -> Iterator[None]:
    """Reset correlation/trace-id context variables between every test.

    Without this, a test that sets a correlation or trace id via
    :func:`~meca_engine.logging_.correlation.correlation_scope` /
    :func:`~meca_engine.logging_.correlation.trace_scope` and fails before
    the context manager exits could leak that id into an unrelated,
    later-running test.
    """
    reset_context()
    yield
    reset_context()
