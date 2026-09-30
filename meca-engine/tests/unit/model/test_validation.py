"""Unit tests for meca_engine.model.validation."""

from __future__ import annotations

from dataclasses import replace

import pytest

from meca_engine.model.article import Affiliation, ArticleModel, Contributor, RoundInfo
from meca_engine.model.enums import ContribType
from meca_engine.model.validation import StructuralIssueSeverity, validate_structural_integrity

pytestmark = pytest.mark.unit


def test_structurally_sound_model_has_no_issues(sample_article_model: ArticleModel) -> None:
    assert validate_structural_integrity(sample_article_model) == ()


def test_duplicate_affiliation_key_is_reported(sample_article_model: ArticleModel) -> None:
    duplicated = sample_article_model.article_meta.affiliations + (
        Affiliation(model_key=1, institution="Another University"),
    )
    model = replace(
        sample_article_model,
        article_meta=replace(sample_article_model.article_meta, affiliations=duplicated),
    )

    issues = validate_structural_integrity(model)

    assert any(i.code == "DUPLICATE_AFFILIATION_KEY" for i in issues)
    assert all(i.severity is StructuralIssueSeverity.ERROR for i in issues)


def test_dangling_affiliation_reference_is_reported(sample_article_model: ArticleModel) -> None:
    dangling_contributor = Contributor(
        surname="Ghost",
        given_names="No",
        contrib_type=ContribType.AUTHOR,
        affiliation_keys=(999,),
    )
    model = replace(
        sample_article_model,
        article_meta=replace(
            sample_article_model.article_meta,
            contributors=(*sample_article_model.article_meta.contributors, dangling_contributor),
        ),
    )

    issues = validate_structural_integrity(model)

    assert any(i.code == "DANGLING_AFFILIATION_KEY" for i in issues)


def test_zero_is_latest_rounds_is_reported(sample_article_model: ArticleModel) -> None:
    all_not_latest = tuple(replace(r, is_latest=False) for r in sample_article_model.rounds)
    model = replace(sample_article_model, rounds=all_not_latest)

    issues = validate_structural_integrity(model)

    assert any(i.code == "ROUND_LATEST_COUNT_INVALID" for i in issues)


def test_multiple_is_latest_rounds_is_reported(sample_article_model: ArticleModel) -> None:
    all_latest = tuple(replace(r, is_latest=True) for r in sample_article_model.rounds)
    model = replace(sample_article_model, rounds=all_latest)

    issues = validate_structural_integrity(model)

    assert any(i.code == "ROUND_LATEST_COUNT_INVALID" for i in issues)


def test_duplicate_round_sequence_number_is_reported(sample_article_model: ArticleModel) -> None:
    duplicated_rounds = (
        RoundInfo(label="Original", sequence_number=1, is_latest=False),
        RoundInfo(label="R1", sequence_number=1, is_latest=True),
    )
    model = replace(sample_article_model, rounds=duplicated_rounds)

    issues = validate_structural_integrity(model)

    assert any(i.code == "DUPLICATE_ROUND_SEQUENCE" for i in issues)


def test_empty_round_index_produces_no_round_issues(sample_article_model: ArticleModel) -> None:
    model = replace(sample_article_model, rounds=())

    issues = validate_structural_integrity(model)

    assert not any("ROUND" in i.code for i in issues)


def test_validation_logs_start_and_completion(sample_article_model: ArticleModel) -> None:
    import logging

    from meca_engine.logging_.structured_logger import StructuredLogger

    class _ListHandler(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.records: list[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    underlying = logging.getLogger("meca_engine.test.validation_logging")
    handler = _ListHandler()
    underlying.addHandler(handler)
    underlying.setLevel(logging.DEBUG)
    underlying.propagate = False

    logger = StructuredLogger("test.validation_logging")
    validate_structural_integrity(sample_article_model, logger=logger)

    assert len(handler.records) == 2
    underlying.removeHandler(handler)
