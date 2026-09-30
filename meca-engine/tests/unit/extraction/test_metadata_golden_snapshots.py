"""Golden snapshot tests for the Metadata Extraction Layer.

Parses a checked-in, representative fixture XML file, runs every
extractor over it via :func:`~meca_engine.extraction.metadata_extraction.extract_all_metadata`,
and compares the resulting :class:`~meca_engine.extraction.metadata_models.ExtractionBundle`
against a checked-in expected JSON snapshot — the Milestone 4 analogue of
Milestone 3's Parsed Object Model golden snapshot test
(``test_golden_snapshots.py``).

To intentionally update the snapshot after a deliberate, reviewed
behavior change: regenerate it from the fixture, inspect the diff, and
commit the updated JSON alongside the code change in the same PR — never
silently.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from meca_engine.extraction.metadata_extraction import extract_all_metadata
from meca_engine.extraction.xml_loader import XmlLoader
from meca_engine.logging_ import get_logger

from ._metadata_snapshot_utils import extraction_bundle_to_snapshot_dict

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "extraction"


def test_metadata_sample_matches_golden_snapshot() -> None:
    loader = XmlLoader(get_logger("test.metadata_golden_snapshot"))
    fixture_path = _FIXTURES_DIR / "metadata_sample.xml"
    expected_path = _FIXTURES_DIR / "snapshots" / "metadata_sample.snapshot.json"

    document = loader.load(fixture_path)
    bundle = extract_all_metadata(document, get_logger("test.metadata_golden_snapshot"))
    actual_snapshot = extraction_bundle_to_snapshot_dict(bundle)
    expected_snapshot = json.loads(expected_path.read_text(encoding="utf-8"))

    assert actual_snapshot == expected_snapshot


def test_golden_snapshot_fixture_is_never_silently_regenerated_empty() -> None:
    expected_path = _FIXTURES_DIR / "snapshots" / "metadata_sample.snapshot.json"

    expected_snapshot = json.loads(expected_path.read_text(encoding="utf-8"))

    assert expected_snapshot["article"]["title"] == "A Study of Example Practices"
    assert len(expected_snapshot["contributors"]["authors"]) == 2
