"""Run control — file-based pause/resume/stop/cancel signaling for a live batch run.

Deliberately file-based, not sockets: a batch run and its controller (the
Dashboard API, a separate process) communicate by polling a small JSON
file, the lightest mechanism that satisfies "polling is fine, no
websocket complexity" without introducing any new IPC framework.
Optional everywhere it's consumed — a run started without a control/status
path behaves exactly as before this capability existed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@unique
class ControlCommand(str, Enum):
    """A command the controller may request between articles."""

    RUN = "run"
    PAUSE = "pause"
    STOP_AFTER_CURRENT = "stop_after_current"
    CANCEL = "cancel"


@unique
class RunState(str, Enum):
    """The live run's current state, as reported to a poller."""

    PROCESSING = "processing"
    COMPLETED = "completed"
    STOPPED = "stopped"
    CANCELLED = "cancelled"


def read_command(control_path: Path) -> ControlCommand:
    """Return the currently-requested command, defaulting to RUN if absent or unreadable."""
    try:
        raw = json.loads(control_path.read_text())
        return ControlCommand(raw.get("command", ControlCommand.RUN.value))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return ControlCommand.RUN


def write_command(control_path: Path, command: ControlCommand) -> None:
    """Write a control command for a running batch to pick up on its next check."""
    control_path.parent.mkdir(parents=True, exist_ok=True)
    control_path.write_text(json.dumps({"command": command.value}))


def wait_while_paused(control_path: Path, *, poll_seconds: float = 1.0) -> ControlCommand:
    """Block while the control file says PAUSE; return the command that ended the wait."""
    while True:
        command = read_command(control_path)
        if command is not ControlCommand.PAUSE:
            return command
        time.sleep(poll_seconds)


@dataclass
class LiveStatusWriter:
    """Writes a live-status JSON snapshot a poller can read while a batch runs."""

    status_path: Path
    total: int
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed: int = 0
    current_article_id: str | None = None

    def start_article(self, article_id: str) -> None:
        """Record which article is now being processed."""
        self.current_article_id = article_id
        self._write(state=RunState.PROCESSING)

    def complete_article(self) -> None:
        """Record that the current article finished."""
        self.completed += 1
        self._write(state=RunState.PROCESSING)

    def finish(self, state: RunState) -> None:
        """Record the run's terminal state."""
        self.current_article_id = None
        self._write(state=state)

    def _write(self, *, state: RunState) -> None:
        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        rate = elapsed / self.completed if self.completed else None
        remaining = self.total - self.completed
        payload = {
            "state": state.value,
            "total": self.total,
            "completed": self.completed,
            "remaining": remaining,
            "current_article_id": self.current_article_id,
            "started_at": self.started_at.isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "estimated_remaining_seconds": round(rate * remaining, 1) if rate else None,
            "articles_per_second": round(1 / rate, 3) if rate else None,
        }
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        self.status_path.write_text(json.dumps(payload))
