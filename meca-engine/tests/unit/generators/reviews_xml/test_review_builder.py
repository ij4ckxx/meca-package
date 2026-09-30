"""Unit tests for meca_engine.generators.reviews_xml.review_builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from meca_engine.generators.diagnostics import DiagnosticsCollector
from meca_engine.generators.reviews_xml.review_builder import (
    build_decline_reviews,
    build_extended_history_reviews,
    build_scorecard_reviews,
)
from meca_engine.generators.xml.builder import XmlDocumentBuilder
from meca_engine.model.article import (
    CorrespondenceEvent,
    DeclineReason,
    ReviewerScorecard,
    WorkflowLog,
)
from meca_engine.model.enums import (
    ActorRole,
    CorrespondenceChannel,
    CorrespondenceKind,
    ReviewOutcomeStatus,
)

if TYPE_CHECKING:
    from meca_engine.config.schema import FeatureFlagsConfig, ReviewsXmlConfig

pytestmark = pytest.mark.unit


def _scorecard(**overrides: object) -> ReviewerScorecard:
    defaults: dict[str, object] = {
        "round_label": "Original",
        "reviewer_name": "Jane Reviewer",
        "reviewer_email": "jane@example.com",
        "outcome_status": ReviewOutcomeStatus.COMPLETED,
        "answers": (("QN_01", "Yes"),),
    }
    defaults.update(overrides)
    return ReviewerScorecard(**defaults)  # type: ignore[arg-type]


# --- scorecards (BR-102/103/104/112) ---------------------------------------------


def test_completed_scorecard_produces_a_review_block(reviews_xml_config: ReviewsXmlConfig) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()

    reviews = build_scorecard_reviews(builder, reviews_xml_config, (_scorecard(),), diagnostics)

    assert len(reviews) == 1
    review = reviews[0]
    assert review.get("review-version") == "Original"
    assert review.get("review-type") == "review"
    assert review.get("blinding") == "single"
    assert review.get("permission-to-publish") == "yes"
    assert review.get("permission-to-transfer") == "yes"
    data = review.find("review-item-group/review-item/review-item-response/review-item-data")
    assert data is not None
    assert data.text == "QN_01: Yes"
    email = review.find("contrib-group/contrib/email")
    assert email is not None
    assert email.text == "jane@example.com"


def test_missing_overall_recommendation_is_diagnosed(reviews_xml_config: ReviewsXmlConfig) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()

    build_scorecard_reviews(builder, reviews_xml_config, (_scorecard(),), diagnostics)

    assert any("overall_recommendation" in d.message for d in diagnostics.diagnostics)


def test_populated_overall_recommendation_suppresses_the_missing_diagnostic(
    reviews_xml_config: ReviewsXmlConfig,
) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()

    build_scorecard_reviews(
        builder, reviews_xml_config, (_scorecard(overall_recommendation="Accept"),), diagnostics
    )

    assert not any("overall_recommendation" in d.message for d in diagnostics.diagnostics)


def test_scorecard_with_no_answers_is_diagnosed(reviews_xml_config: ReviewsXmlConfig) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()

    build_scorecard_reviews(builder, reviews_xml_config, (_scorecard(answers=()),), diagnostics)

    assert any("no answers" in d.message for d in diagnostics.diagnostics)


def test_non_completed_outcome_status_renders_as_status_only(
    reviews_xml_config: ReviewsXmlConfig,
) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()

    reviews = build_scorecard_reviews(
        builder,
        reviews_xml_config,
        (_scorecard(outcome_status=ReviewOutcomeStatus.PENDING),),
        diagnostics,
    )

    assert len(reviews) == 1
    item = reviews[0].find("review-item-group/review-item")
    assert item is not None
    assert item.get("review-item-type") == "correspondence"
    assert any("outcome_status" in d.message for d in diagnostics.diagnostics)


def test_scorecard_with_recommendation_but_no_identity_recovers_with_a_warning(
    reviews_xml_config: ReviewsXmlConfig,
) -> None:
    """Milestone 11: real review content is kept, identity is omitted, no raise."""
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    scorecard = _scorecard(reviewer_name="", reviewer_email="", overall_recommendation="Accept")

    reviews = build_scorecard_reviews(builder, reviews_xml_config, (scorecard,), diagnostics)

    assert len(reviews) == 1
    assert any(
        "recommendation but no reviewer identity" in d.message and "recoverable" in d.message
        for d in diagnostics.diagnostics
    )


def test_scorecard_with_no_identity_and_no_recommendation_is_diagnosed_not_raised(
    reviews_xml_config: ReviewsXmlConfig,
) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    scorecard = _scorecard(reviewer_name="", reviewer_email="")

    reviews = build_scorecard_reviews(builder, reviews_xml_config, (scorecard,), diagnostics)

    assert len(reviews) == 1
    assert any("no name/email" in d.message for d in diagnostics.diagnostics)


# --- decline reasons (BR-106/107/125) ---------------------------------------------


def test_decline_reason_produces_a_status_only_review(reviews_xml_config: ReviewsXmlConfig) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    decline = DeclineReason(
        round_label="Original", reviewer_name="David Kaye", reason_text="Unavailable"
    )

    reviews = build_decline_reviews(builder, reviews_xml_config, (decline,), diagnostics)

    assert len(reviews) == 1
    review = reviews[0]
    item = review.find("review-item-group/review-item")
    assert item is not None
    assert item.get("review-item-type") == "correspondence"
    data = item.find("review-item-response/review-item-data")
    assert data is not None
    assert data.text == "Unavailable"
    assert review.find("contrib-group/contrib/email") is None  # no email field on DeclineReason


def test_decline_reason_with_no_name_is_diagnosed(reviews_xml_config: ReviewsXmlConfig) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    decline = DeclineReason(round_label="Original", reviewer_name="", reason_text="Unavailable")

    build_decline_reviews(builder, reviews_xml_config, (decline,), diagnostics)

    assert any("no reviewer name" in d.message for d in diagnostics.diagnostics)


# --- extended history / duplicate correspondence (ADR-004/005, BR-108/111/116-119) ---


def _event(**overrides: object) -> CorrespondenceEvent:
    from datetime import datetime

    defaults: dict[str, object] = {
        "timestamp": datetime(2025, 1, 1),
        "actor_name": "Jane Reviewer",
        "actor_role": ActorRole.REVIEWER,
        "channel": CorrespondenceChannel.TO_EDITOR_CONFIDENTIAL,
        "event_kind": CorrespondenceKind.REVIEW_COMMENT,
        "text": "Duplicate correspondence text",
    }
    defaults.update(overrides)
    return CorrespondenceEvent(**defaults)  # type: ignore[arg-type]


def test_duplicate_correspondence_included_when_flag_enabled(
    reviews_xml_config: ReviewsXmlConfig, enabled_feature_flags: FeatureFlagsConfig
) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    workflow_log = WorkflowLog(events=(_event(),))

    reviews = build_extended_history_reviews(
        builder, reviews_xml_config, enabled_feature_flags, workflow_log, diagnostics
    )

    assert len(reviews) == 1


def test_duplicate_correspondence_excluded_when_flag_disabled(
    reviews_xml_config: ReviewsXmlConfig, disabled_feature_flags: FeatureFlagsConfig
) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    workflow_log = WorkflowLog(events=(_event(),))

    reviews = build_extended_history_reviews(
        builder, reviews_xml_config, disabled_feature_flags, workflow_log, diagnostics
    )

    assert reviews == ()


@pytest.mark.parametrize(
    "event_kind",
    [
        CorrespondenceKind.SCREENING_QUERY,
        CorrespondenceKind.EDITOR_REASSIGNMENT,
        CorrespondenceKind.AUTHOR_SUGGESTED_REVIEWER,
        CorrespondenceKind.PRODUCTION_QUERY,
    ],
)
def test_extended_scope_events_gated_by_extended_history_flag(
    reviews_xml_config: ReviewsXmlConfig,
    enabled_feature_flags: FeatureFlagsConfig,
    disabled_feature_flags: FeatureFlagsConfig,
    event_kind: CorrespondenceKind,
) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    workflow_log = WorkflowLog(events=(_event(event_kind=event_kind),))

    enabled = build_extended_history_reviews(
        builder, reviews_xml_config, enabled_feature_flags, workflow_log, diagnostics
    )
    disabled = build_extended_history_reviews(
        builder, reviews_xml_config, disabled_feature_flags, workflow_log, diagnostics
    )

    assert len(enabled) == 1
    assert disabled == ()


def test_attachment_url_produces_an_ext_link_br_108(
    reviews_xml_config: ReviewsXmlConfig, enabled_feature_flags: FeatureFlagsConfig
) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    workflow_log = WorkflowLog(
        events=(_event(attachment_url="https://ppl.kriyadocs.com/resources/x.pdf"),)
    )

    reviews = build_extended_history_reviews(
        builder, reviews_xml_config, enabled_feature_flags, workflow_log, diagnostics
    )

    ext_link = reviews[0].find("review-item-group/review-item/ext-link")
    assert ext_link is not None
    assert ext_link.get("xlink:href") == "https://ppl.kriyadocs.com/resources/x.pdf"


def test_unsupported_event_kind_is_diagnosed_and_skipped(
    reviews_xml_config: ReviewsXmlConfig, enabled_feature_flags: FeatureFlagsConfig
) -> None:
    from unittest.mock import MagicMock

    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    bogus_kind = MagicMock()
    bogus_kind.value = "unsupported_kind"
    workflow_log = WorkflowLog(events=(_event(event_kind=bogus_kind),))

    reviews = build_extended_history_reviews(
        builder, reviews_xml_config, enabled_feature_flags, workflow_log, diagnostics
    )

    assert reviews == ()
    assert any("unsupported event_kind" in d.message for d in diagnostics.diagnostics)


def test_empty_workflow_log_produces_no_reviews(
    reviews_xml_config: ReviewsXmlConfig, enabled_feature_flags: FeatureFlagsConfig
) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()

    reviews = build_extended_history_reviews(
        builder, reviews_xml_config, enabled_feature_flags, WorkflowLog(), diagnostics
    )

    assert reviews == ()
