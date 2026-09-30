"""Unit tests for meca_engine.model.enums."""

from __future__ import annotations

import pytest

from meca_engine.model.enums import (
    ActorRole,
    ContribType,
    CorrespondenceChannel,
    CorrespondenceKind,
    ReviewOutcomeStatus,
)

pytestmark = pytest.mark.unit


def test_contrib_type_values() -> None:
    assert {member.value for member in ContribType} == {
        "author",
        "reviewer",
        "handling_editor",
        "associate_editor",
        "academic_editor",
        "guest_editor",
        "production_editor",
        "copy_editor",
        "other",
    }


def test_review_outcome_status_values() -> None:
    assert {member.value for member in ReviewOutcomeStatus} == {
        "completed",
        "declined",
        "terminated",
        "pending",
    }


def test_actor_role_values() -> None:
    assert {member.value for member in ActorRole} == {
        "reviewer",
        "editor",
        "associate_editor",
        "author",
        "publisher",
        "copyeditor",
        "preeditor",
    }


def test_correspondence_channel_values() -> None:
    assert {member.value for member in CorrespondenceChannel} == {
        "to_author",
        "to_editor_confidential",
        "internal",
    }


def test_correspondence_kind_values() -> None:
    assert {member.value for member in CorrespondenceKind} == {
        "review_comment",
        "screening_query",
        "editor_reassignment",
        "author_suggested_reviewer",
        "production_query",
    }
