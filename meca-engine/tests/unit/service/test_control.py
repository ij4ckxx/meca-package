"""Unit tests for meca_engine.service.control."""

from __future__ import annotations

import json
import threading
import time
from typing import TYPE_CHECKING

import pytest

from meca_engine.service.control import (
    ControlCommand,
    LiveStatusWriter,
    RunState,
    read_command,
    wait_while_paused,
    write_command,
)

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def test_read_command_defaults_to_run_when_file_missing(tmp_path: Path) -> None:
    assert read_command(tmp_path / "control.json") is ControlCommand.RUN


def test_write_then_read_command_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "control.json"
    write_command(path, ControlCommand.CANCEL)

    assert read_command(path) is ControlCommand.CANCEL


def test_wait_while_paused_returns_immediately_when_not_paused(tmp_path: Path) -> None:
    path = tmp_path / "control.json"
    write_command(path, ControlCommand.RUN)

    assert wait_while_paused(path, poll_seconds=5.0) is ControlCommand.RUN


def test_wait_while_paused_blocks_until_resumed(tmp_path: Path) -> None:
    path = tmp_path / "control.json"
    write_command(path, ControlCommand.PAUSE)

    def resume_soon() -> None:
        time.sleep(0.05)
        write_command(path, ControlCommand.RUN)

    threading.Thread(target=resume_soon).start()
    started = time.perf_counter()
    result = wait_while_paused(path, poll_seconds=0.01)
    elapsed = time.perf_counter() - started

    assert result is ControlCommand.RUN
    assert elapsed >= 0.04


def test_live_status_writer_reports_progress(tmp_path: Path) -> None:
    path = tmp_path / "live_status.json"
    writer = LiveStatusWriter(status_path=path, total=2)

    writer.start_article("a-1")
    snapshot = json.loads(path.read_text())
    assert snapshot["state"] == "processing"
    assert snapshot["current_article_id"] == "a-1"
    assert snapshot["completed"] == 0

    writer.complete_article()
    writer.finish(RunState.COMPLETED)
    snapshot = json.loads(path.read_text())
    assert snapshot["state"] == "completed"
    assert snapshot["completed"] == 1
    assert snapshot["current_article_id"] is None
