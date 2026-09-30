"""Unit tests for meca_engine.generators.reviews_xml.generator.ReviewsXmlGenerator."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from xml.etree.ElementTree import fromstring

import pytest

from meca_engine.exceptions import GeneratorInvariantError
from meca_engine.generators.result import GenerationResult
from meca_engine.generators.reviews_xml.generator import ReviewsXmlGenerator
from meca_engine.generators.xml.namespaces import NamespaceManager
from meca_engine.model.article import CustomMetaStore, ReviewerScorecard, RoundInfo
from meca_engine.model.enums import ReviewOutcomeStatus

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from meca_engine.config.schema import ReviewsXmlConfig
    from meca_engine.generators.context import GeneratorContext
    from meca_engine.generators.reviews_xml.document import ReviewsXmlDocument

pytestmark = pytest.mark.unit

_NS = {"r": "https://manuscriptexchange.org/schema/reviews"}


def _decode(document: ReviewsXmlDocument) -> str:
    return document.xml_bytes.decode("utf-8")


def _reviews(document: ReviewsXmlDocument) -> list[Element]:
    root = fromstring(document.xml_bytes)
    return root.findall("r:review", _NS)


# --- lifecycle / framework usage ----------------------------------------------


def test_generator_name_is_reviews_xml(reviews_xml_generator: ReviewsXmlGenerator) -> None:
    assert reviews_xml_generator.generator_name == "reviews_xml"


def test_generate_returns_a_generation_result(
    reviews_xml_generator: ReviewsXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = reviews_xml_generator.generate(rich_context)

    assert isinstance(result, GenerationResult)
    assert result.article_id == "cs-2025-0001"
    assert result.generator_name == "reviews_xml"
    assert result.duration_ms >= 0


def test_filename_matches_br_122_pattern(
    reviews_xml_generator: ReviewsXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = reviews_xml_generator.generate(rich_context)

    assert result.document.filename == "cs-2025-0001_reviews.xml"


def test_output_is_well_formed_xml(
    reviews_xml_generator: ReviewsXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = reviews_xml_generator.generate(rich_context)

    fromstring(result.document.xml_bytes)  # raises if not well-formed


# --- root / DOCTYPE / namespaces (BR-096/097/120/121) ---------------------------


def test_xml_declaration_matches_br_120(
    reviews_xml_generator: ReviewsXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(reviews_xml_generator.generate(rich_context).document)

    assert output.startswith('<?xml version="1.0" encoding="UTF-8"?>')


def test_no_byte_order_mark_br_121(
    reviews_xml_generator: ReviewsXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = reviews_xml_generator.generate(rich_context)

    assert not result.document.xml_bytes.startswith(b"\xef\xbb\xbf")


def test_doctype_matches_br_096(
    reviews_xml_generator: ReviewsXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(reviews_xml_generator.generate(rich_context).document)

    assert (
        '<!DOCTYPE review-group PUBLIC "-//MECA//DTD Reviews v1.0//en" "../DTD/reviews-1.0.dtd">'
        in output
    )


def test_root_declares_default_xlink_and_ali_namespaces_br_096(
    reviews_xml_generator: ReviewsXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(reviews_xml_generator.generate(rich_context).document.xml_bytes)

    assert root.tag == "{https://manuscriptexchange.org/schema/reviews}review-group"


def test_content_version_matches_br_097(
    reviews_xml_generator: ReviewsXmlGenerator, rich_context: GeneratorContext
) -> None:
    root = fromstring(reviews_xml_generator.generate(rich_context).document.xml_bytes)

    assert root.get("content-version") == "1.0"


@pytest.mark.parametrize("missing_prefix", ["meca-reviews", "xlink", "ali"])
def test_unregistered_namespace_raises_generator_invariant_error(
    reviews_xml_config: ReviewsXmlConfig,
    rich_context: GeneratorContext,
    missing_prefix: str,
) -> None:
    registry = {
        "xlink": "http://www.w3.org/1999/xlink",
        "ali": "http://www.niso.org/schemas/ali/1.0/",
        "meca-reviews": "https://manuscriptexchange.org/schema/reviews",
    }
    del registry[missing_prefix]
    generator = ReviewsXmlGenerator(
        namespace_manager=NamespaceManager(registry), reviews_xml_config=reviews_xml_config
    )

    with pytest.raises(GeneratorInvariantError):
        generator.generate(rich_context)


# --- ordering (BR-123) -----------------------------------------------------------


def test_reviews_ordered_before_decision_within_a_round(
    reviews_xml_generator: ReviewsXmlGenerator, rich_context: GeneratorContext
) -> None:
    reviews = _reviews(reviews_xml_generator.generate(rich_context).document)

    review_types = [r.get("review-type") for r in reviews]
    assert review_types.index("decision") == len(review_types) - 1


def test_rounds_ordered_ascending_by_sequence_number(
    reviews_xml_generator: ReviewsXmlGenerator, rich_context: GeneratorContext
) -> None:
    custom_meta = CustomMetaStore(
        reviewer_scorecards=(
            ReviewerScorecard(
                round_label="R1",
                reviewer_name="Later Reviewer",
                reviewer_email="later@example.com",
                outcome_status=ReviewOutcomeStatus.COMPLETED,
                answers=(),
            ),
            ReviewerScorecard(
                round_label="Original",
                reviewer_name="Earlier Reviewer",
                reviewer_email="earlier@example.com",
                outcome_status=ReviewOutcomeStatus.COMPLETED,
                answers=(),
            ),
        ),
    )
    context = replace(
        rich_context,
        model=replace(
            rich_context.model,
            custom_meta=custom_meta,
            rounds=(
                RoundInfo(label="Original", sequence_number=1, is_latest=False),
                RoundInfo(label="R1", sequence_number=2, is_latest=True),
            ),
        ),
    )

    reviews = _reviews(reviews_xml_generator.generate(context).document)

    assert [r.get("review-version") for r in reviews] == ["Original", "R1"]


def test_unresolved_round_label_sorted_last_and_diagnosed(
    reviews_xml_generator: ReviewsXmlGenerator, rich_context: GeneratorContext
) -> None:
    custom_meta = CustomMetaStore(
        reviewer_scorecards=(
            ReviewerScorecard(
                round_label="R1",
                reviewer_name="Unresolved Round Reviewer",
                reviewer_email="r1@example.com",
                outcome_status=ReviewOutcomeStatus.COMPLETED,
                answers=(),
            ),
            ReviewerScorecard(
                round_label="Original",
                reviewer_name="Resolved Round Reviewer",
                reviewer_email="orig@example.com",
                outcome_status=ReviewOutcomeStatus.COMPLETED,
                answers=(),
            ),
        ),
    )
    context = replace(
        rich_context,
        model=replace(
            rich_context.model,
            custom_meta=custom_meta,
            rounds=(RoundInfo(label="Original", sequence_number=1, is_latest=True),),
        ),
    )

    result = reviews_xml_generator.generate(context)
    reviews = _reviews(result.document)

    assert [r.get("review-version") for r in reviews] == ["Original", "R1"]
    assert any("does not match any round" in d.message for d in result.diagnostics)


# --- diagnostics / edge cases ------------------------------------------------------


def test_no_review_or_decision_history_is_diagnosed(
    reviews_xml_generator: ReviewsXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = reviews_xml_generator.generate(empty_context)

    assert _reviews(result.document) == []
    assert any("No review or decision history" in d.message for d in result.diagnostics)


def test_missing_recommendation_is_diagnosed_not_fabricated(
    reviews_xml_generator: ReviewsXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = reviews_xml_generator.generate(rich_context)

    assert any("overall_recommendation" in d.message for d in result.diagnostics)
    output = _decode(result.document)
    assert 'review-item-type="recommendation"' not in output


def test_missing_editor_identity_and_decision_date_are_diagnosed(
    reviews_xml_generator: ReviewsXmlGenerator, rich_context: GeneratorContext
) -> None:
    result = reviews_xml_generator.generate(rich_context)

    assert any("editor/associate-editor identity" in d.message for d in result.diagnostics)
    assert any("decision_date" in d.message for d in result.diagnostics)


def test_every_optional_field_missing_still_produces_a_document(
    reviews_xml_generator: ReviewsXmlGenerator, empty_context: GeneratorContext
) -> None:
    result = reviews_xml_generator.generate(empty_context)

    assert result.document.xml_bytes
    fromstring(result.document.xml_bytes)


def test_output_uses_two_space_hierarchical_indentation(
    reviews_xml_generator: ReviewsXmlGenerator, rich_context: GeneratorContext
) -> None:
    output = _decode(reviews_xml_generator.generate(rich_context).document)

    assert "\n  <review " in output
