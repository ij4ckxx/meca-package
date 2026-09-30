"""Unit tests for meca_engine.validation.dtd_issue_classifier."""

from __future__ import annotations

import pytest

from meca_engine.validation.dtd_issue_classifier import SpecAlignmentCategory, classify_dtd_issue

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        # BR-161/162/163 already fix these at generation time — a
        # residual occurrence falls through to the safe default.
        (
            "No declaration for attribute data-type of element p",
            SpecAlignmentCategory.VALIDATION_ONLY,
        ),
        (
            "Syntax of value for attribute rid of xref is not valid",
            SpecAlignmentCategory.VALIDATION_ONLY,
        ),
        ("No declaration for element string-name", SpecAlignmentCategory.VALIDATION_ONLY),
        ("ID aff1 already defined", SpecAlignmentCategory.SOURCE_DATA_ISSUE),
        ("ID cor1 already defined", SpecAlignmentCategory.SOURCE_DATA_ISSUE),
        # Regression (production-stabilization milestone): the same
        # reasoning applies regardless of id prefix — con1..con14 repeat
        # with genuinely different content across separate editorial
        # rounds in some real sources (25/97 articles in the corpus).
        ("ID con1 already defined", SpecAlignmentCategory.SOURCE_DATA_ISSUE),
        (
            "Element fn content does not follow the DTD, expecting (label? , p+)",
            SpecAlignmentCategory.VALIDATION_ONLY,
        ),
        (
            "No declaration for attribute target of element ext-link",
            SpecAlignmentCategory.VALIDATION_ONLY,
        ),
        ("No declaration for attribute dir of element p", SpecAlignmentCategory.VALIDATION_ONLY),
        (
            "No declaration for attribute award-id-type of element award-id",
            SpecAlignmentCategory.VALIDATION_ONLY,
        ),
    ],
)
def test_classifies_known_issue_patterns(message: str, expected: SpecAlignmentCategory) -> None:
    assert classify_dtd_issue(message) is expected


def test_unrecognized_message_falls_back_to_validation_only() -> None:
    assert (
        classify_dtd_issue("Some brand-new DTD complaint never catalogued before")
        is SpecAlignmentCategory.VALIDATION_ONLY
    )
