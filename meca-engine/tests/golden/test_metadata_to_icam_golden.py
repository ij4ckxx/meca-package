"""Golden-file regression: Metadata → ICAM, against the 3 real reference packages.

Per the current task's explicit requirement: runs the complete Milestone
3 → 4 → 5B pipeline (parse → extract → transform) against each of the 3
real, manually-created reference packages and compares the resulting
frozen `ArticleModel`'s JSON representation
(`model.serialization.to_dict`) against a checked-in golden snapshot —
this milestone's analogue of Milestones 3/4/5A's own golden snapshot
tests, one layer further down the pipeline.

Marked `pytest.mark.golden` (see pyproject.toml's marker definition:
"mandatory merge gate") and deliberately outside `testpaths` (which lists
only `tests/unit`/`tests/integration`) — these tests extract real,
multi-megabyte zip archives and are not meant to run as part of the fast
default suite; see `tests/golden/README.md`.

To intentionally update a snapshot after a deliberate, reviewed pipeline
change: regenerate it from the real sample, inspect the diff, and commit
the updated JSON alongside the code change in the same PR — never
silently.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from meca_engine.config.schema import MediaTypeConfig
from meca_engine.extraction.metadata_extraction import extract_all_metadata
from meca_engine.extraction.xml_loader import XmlLoader
from meca_engine.logging_ import get_logger
from meca_engine.model.serialization import to_dict
from meca_engine.model.validation import validate_structural_integrity
from meca_engine.transform.coordinator import TransformationCoordinator

if TYPE_CHECKING:
    from .conftest import ExtractedSample

pytestmark = [pytest.mark.golden]

_EXPECTED_OUTPUT_DIR = Path(__file__).resolve().parent / "expected_output"

_MEDIA_TYPE_CONFIG = MediaTypeConfig(
    mappings={
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".pdf": "application/pdf",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
    unmapped_extension_policy="warn_and_default",
    unmapped_extension_default="application/octet-stream",
)


def _normalize_staged_paths(snapshot: dict[str, object]) -> dict[str, object]:
    # `staged_physical_path` is an absolute path rooted in a fresh
    # pytest `tmp_path` every run — environment-specific, not a fact
    # about the article, so it is normalized to a basename here before
    # comparison (the same "exclude environment-specific fields"
    # discipline Milestones 3-4's own snapshot serializers apply to
    # e.g. `source_path`), never in `model.serialization.to_dict` itself
    # (a legitimate, real field for production use).
    article = snapshot["article"]
    assert isinstance(article, dict)
    resolved_files = article["resolved_files"]
    assert isinstance(resolved_files, list)
    for resolved_file in resolved_files:
        assert isinstance(resolved_file, dict)
        resolved_file["staged_physical_path"] = Path(resolved_file["staged_physical_path"]).name
    return snapshot


def _build_icam_snapshot(sample: ExtractedSample) -> dict[str, object]:
    logger = get_logger(f"golden.{sample.article_id}")
    loader = XmlLoader(logger)
    document = loader.load(sample.xml_path)
    bundle = extract_all_metadata(document, logger)

    coordinator = TransformationCoordinator(media_type_config=_MEDIA_TYPE_CONFIG, logger=logger)
    model = coordinator.build_model(
        article_id=sample.article_id,
        source_object_key=f"{sample.article_id}/{sample.xml_path.name}",
        staged_root=str(sample.staged_root),
        parsed_document=document,
        extraction_bundle=bundle,
    )

    assert validate_structural_integrity(model) == ()
    return _normalize_staged_paths(to_dict(model))


def test_real_sample_produces_a_structurally_sound_icam(real_sample: ExtractedSample) -> None:
    snapshot = _build_icam_snapshot(real_sample)

    expected_path = _EXPECTED_OUTPUT_DIR / f"{real_sample.article_id}.icam.snapshot.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    assert snapshot == expected
