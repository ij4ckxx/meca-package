"""Golden snapshot test for the ICAM JSON representation.

Per the current task's explicit "Create golden snapshot tests for the
ICAM JSON representation" requirement — the Milestone 5A analogue of
Milestone 3's Parsed Object Model snapshot and Milestone 4's Extracted
Metadata snapshot. Unlike those two, there is no XML fixture to parse
here: the ICAM is built directly (via `ArticleModelBuilder`, exercising
every sub-object), then `model.serialization.to_dict()`'s output is
compared against a checked-in golden JSON file.

To intentionally update the snapshot after a deliberate, reviewed
behavior change: regenerate it from this module's fixture, inspect the
diff, and commit the updated JSON alongside the code change in the same
PR — never silently.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from meca_engine.model.serialization import to_dict

from .conftest import build_sample_article_model

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "model"


def test_sample_article_model_matches_golden_snapshot() -> None:
    expected_path = _FIXTURES_DIR / "snapshots" / "sample_article_model.snapshot.json"

    actual_snapshot = to_dict(build_sample_article_model())
    expected_snapshot = json.loads(expected_path.read_text(encoding="utf-8"))

    assert actual_snapshot == expected_snapshot


def test_golden_snapshot_fixture_is_never_silently_regenerated_empty() -> None:
    expected_path = _FIXTURES_DIR / "snapshots" / "sample_article_model.snapshot.json"

    expected_snapshot = json.loads(expected_path.read_text(encoding="utf-8"))

    assert expected_snapshot["article"]["article_meta"]["article_title"] == (
        "A Study of Example Practices"
    )
    assert len(expected_snapshot["article"]["article_meta"]["contributors"]) == 1
