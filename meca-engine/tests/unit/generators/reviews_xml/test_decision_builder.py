"""Unit tests for meca_engine.generators.reviews_xml.decision_builder."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pytest

from meca_engine.generators.diagnostics import DiagnosticsCollector
from meca_engine.generators.reviews_xml.decision_builder import build_decision_reviews
from meca_engine.generators.xml.builder import XmlDocumentBuilder
from meca_engine.model.article import DecisionDraft

if TYPE_CHECKING:
    from meca_engine.config.schema import ReviewsXmlConfig

pytestmark = pytest.mark.unit


def test_decision_draft_produces_a_decision_review(reviews_xml_config: ReviewsXmlConfig) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    draft = DecisionDraft(round_label="Original", decision_text="Accepted with minor revisions.")

    decisions = build_decision_reviews(builder, reviews_xml_config, (draft,), diagnostics)

    assert len(decisions) == 1
    review = decisions[0]
    assert review.get("review-version") == "Original"
    assert review.get("review-type") == "decision"
    assert review.get("blinding") is None  # BR-098 is review-type=review only
    data = review.find("review-item-group/review-item/review-item-response/review-item-data")
    assert data is not None
    assert data.text == "Accepted with minor revisions."


def test_decision_draft_with_no_text_is_diagnosed_and_skipped(
    reviews_xml_config: ReviewsXmlConfig,
) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    draft = DecisionDraft(round_label="Original", decision_text="")

    decisions = build_decision_reviews(builder, reviews_xml_config, (draft,), diagnostics)

    assert decisions == ()
    assert any("no text" in d.message for d in diagnostics.diagnostics)


def test_missing_editor_identity_is_diagnosed(reviews_xml_config: ReviewsXmlConfig) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    draft = DecisionDraft(round_label="Original", decision_text="Accept.")

    build_decision_reviews(builder, reviews_xml_config, (draft,), diagnostics)

    assert any("editor/associate-editor identity" in d.message for d in diagnostics.diagnostics)


def test_populated_editor_name_produces_editor_contrib_and_suppresses_diagnostic(
    reviews_xml_config: ReviewsXmlConfig,
) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    draft = DecisionDraft(
        round_label="Original", decision_text="Accept.", editor_name="Karin Jandeleit-Dahm"
    )

    decisions = build_decision_reviews(builder, reviews_xml_config, (draft,), diagnostics)

    editor_contrib = decisions[0].find("contrib-group/contrib[@contrib-type='editor']/string-name")
    assert editor_contrib is not None
    assert editor_contrib.text == "Karin Jandeleit-Dahm"
    assert not any("editor/associate-editor identity" in d.message for d in diagnostics.diagnostics)


def test_populated_associate_editor_name_produces_associate_editor_contrib(
    reviews_xml_config: ReviewsXmlConfig,
) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    draft = DecisionDraft(
        round_label="Original", decision_text="Accept.", associate_editor_name="Michael Ryan"
    )

    decisions = build_decision_reviews(builder, reviews_xml_config, (draft,), diagnostics)

    contrib = decisions[0].find(
        "contrib-group/contrib[@contrib-type='associate-editor']/string-name"
    )
    assert contrib is not None
    assert contrib.text == "Michael Ryan"


def test_missing_decision_date_is_diagnosed(reviews_xml_config: ReviewsXmlConfig) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    draft = DecisionDraft(round_label="Original", decision_text="Accept.")

    build_decision_reviews(builder, reviews_xml_config, (draft,), diagnostics)

    assert any("No decision_date" in d.message for d in diagnostics.diagnostics)


def test_populated_decision_date_suppresses_the_missing_diagnostic(
    reviews_xml_config: ReviewsXmlConfig,
) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    draft = DecisionDraft(
        round_label="Original", decision_text="Accept.", decision_date=date(2025, 8, 6)
    )

    build_decision_reviews(builder, reviews_xml_config, (draft,), diagnostics)

    assert not any("no decision_date" in d.message for d in diagnostics.diagnostics)


def test_multiple_decision_drafts_produce_one_review_each(
    reviews_xml_config: ReviewsXmlConfig,
) -> None:
    builder = XmlDocumentBuilder()
    diagnostics = DiagnosticsCollector()
    drafts = (
        DecisionDraft(round_label="Original", decision_text="Major revisions requested."),
        DecisionDraft(round_label="R1", decision_text="Accepted."),
    )

    decisions = build_decision_reviews(builder, reviews_xml_config, drafts, diagnostics)

    assert [d.get("review-version") for d in decisions] == ["Original", "R1"]
