"""Unit tests for meca_engine.transform.workflow_transformer."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from meca_engine.model.article import CorrespondenceEvent, CustomMetaStore, WorkflowLog
from meca_engine.model.enums import ActorRole, CorrespondenceChannel, CorrespondenceKind
from meca_engine.transform.workflow_transformer import build_workflow_log

pytestmark = pytest.mark.unit


def test_returns_the_stores_own_workflow_log_unchanged() -> None:
    event = CorrespondenceEvent(
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        actor_name="Editor",
        actor_role=ActorRole.EDITOR,
        channel=CorrespondenceChannel.TO_AUTHOR,
        event_kind=CorrespondenceKind.REVIEW_COMMENT,
        text="Hello",
    )
    store = CustomMetaStore(workflow_log=WorkflowLog(events=(event,)))

    result = build_workflow_log(store)

    assert result is store.workflow_log


def test_empty_store_produces_empty_workflow_log() -> None:
    store = CustomMetaStore()

    result = build_workflow_log(store)

    assert result.events == ()
