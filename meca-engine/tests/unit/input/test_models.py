"""Unit tests for meca_engine.input.models."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from pathlib import Path

import pytest

from meca_engine.input.models import (
    ArticleReference,
    FileInventory,
    FileRecord,
    LocalBatchSource,
)

pytestmark = pytest.mark.unit


def test_local_batch_source_is_frozen() -> None:
    source = LocalBatchSource(root_path=Path("/tmp/batch"))

    with pytest.raises(dataclasses.FrozenInstanceError):
        source.root_path = Path("/other")  # type: ignore[misc]


def test_file_record_with_staging_result_returns_new_instance() -> None:
    original = FileRecord(round_label="Original", relative_path="manuscript.txt", size_bytes=42)

    staged = original.with_staging_result(checksum="abc123", staged_local_path=Path("/work/x"))

    assert staged.checksum == "abc123"
    assert staged.staged_local_path == Path("/work/x")
    assert original.checksum is None  # original untouched
    assert staged.round_label == original.round_label
    assert staged.relative_path == original.relative_path
    assert staged.size_bytes == original.size_bytes


def test_file_inventory_total_size_bytes() -> None:
    inventory = FileInventory(
        files=(
            FileRecord(round_label="Original", relative_path="a.txt", size_bytes=10),
            FileRecord(round_label="Original", relative_path="b.txt", size_bytes=20),
            FileRecord(round_label="R1", relative_path="a.txt", size_bytes=5),
        )
    )

    assert inventory.total_size_bytes == 35


def test_file_inventory_by_round() -> None:
    inventory = FileInventory(
        files=(
            FileRecord(round_label="Original", relative_path="a.txt", size_bytes=10),
            FileRecord(round_label="R1", relative_path="a.txt", size_bytes=5),
        )
    )

    original_files = inventory.by_round("Original")

    assert len(original_files) == 1
    assert original_files[0].relative_path == "a.txt"
    assert original_files[0].round_label == "Original"


def test_file_inventory_round_labels_preserves_first_seen_order() -> None:
    inventory = FileInventory(
        files=(
            FileRecord(round_label="R1", relative_path="a.txt", size_bytes=1),
            FileRecord(round_label="Original", relative_path="b.txt", size_bytes=1),
            FileRecord(round_label="R1", relative_path="c.txt", size_bytes=1),
        )
    )

    assert inventory.round_labels == ("R1", "Original")


def test_file_inventory_defaults_to_empty() -> None:
    inventory = FileInventory()

    assert inventory.files == ()
    assert inventory.anomalous_relative_paths == ()
    assert inventory.total_size_bytes == 0
    assert inventory.round_labels == ()


def test_article_reference_is_frozen() -> None:
    reference = ArticleReference(
        article_id="ART-0001",
        source=LocalBatchSource(root_path=Path("/tmp/batch")),
        root_xml_relative_name="ART-0001.xml",
        file_inventory=FileInventory(),
        discovered_at=datetime.now(timezone.utc),
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        reference.article_id = "CHANGED"  # type: ignore[misc]
