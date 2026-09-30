"""Golden snapshot tests for the Parsed Object Model.

Per the current task's explicit requirement: parses a checked-in,
representative fixture XML file and compares the resulting
``ParsedDocument``'s structure against a checked-in expected JSON
snapshot. Any unintended change in parsing behavior (namespace
resolution, text/tail handling, DOCTYPE detection, diagnostic
generation, etc.) is caught as a diff here, the same way
`14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md` §11.3's golden-file
regression suite protects the (much later) full generation pipeline.

To intentionally update a snapshot after a deliberate, reviewed behavior
change: re-run the snapshot-generation one-liner in this module's
docstring history (see git blame / PR description), inspect the diff, and
commit the updated JSON alongside the code change in the same PR — never
silently.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from meca_engine.extraction.xml_loader import XmlLoader
from meca_engine.logging_ import get_logger

from ._snapshot_utils import document_to_snapshot_dict

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "extraction"


def test_valid_sample_matches_golden_snapshot() -> None:
    loader = XmlLoader(get_logger("test.golden_snapshot"))
    fixture_path = _FIXTURES_DIR / "valid_sample.xml"
    expected_path = _FIXTURES_DIR / "snapshots" / "valid_sample.snapshot.json"

    document = loader.load(fixture_path)
    actual_snapshot = document_to_snapshot_dict(document)
    expected_snapshot = json.loads(expected_path.read_text(encoding="utf-8"))

    assert actual_snapshot == expected_snapshot


def test_golden_snapshot_fixture_is_never_silently_regenerated_empty() -> None:
    # Guards against the snapshot file itself being accidentally emptied
    # or truncated (e.g. a bad merge) without the comparison test above
    # catching it via a false-positive empty-vs-empty match.
    expected_path = _FIXTURES_DIR / "snapshots" / "valid_sample.snapshot.json"

    expected_snapshot = json.loads(expected_path.read_text(encoding="utf-8"))

    assert expected_snapshot["root"]["tag"] == "article"
    assert expected_snapshot["doctype"] is not None
