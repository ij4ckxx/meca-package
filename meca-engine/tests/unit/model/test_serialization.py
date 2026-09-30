"""Unit tests for meca_engine.model.serialization."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from meca_engine.exceptions import ModelBuildError
from meca_engine.model.article import ArticleMeta, ArticleModel
from meca_engine.model.serialization import SCHEMA_VERSION, from_dict, to_dict

pytestmark = pytest.mark.unit


def test_to_dict_carries_schema_version(sample_article_model: ArticleModel) -> None:
    data = to_dict(sample_article_model)
    assert data["schema_version"] == SCHEMA_VERSION


def test_to_dict_is_json_serializable(sample_article_model: ArticleModel) -> None:
    data = to_dict(sample_article_model)
    # Must not raise — every value is a JSON-safe primitive/list/dict.
    json.dumps(data)


def test_round_trip_preserves_equality(sample_article_model: ArticleModel) -> None:
    data = to_dict(sample_article_model)
    restored = from_dict(data)
    assert restored == sample_article_model


def test_round_trip_through_actual_json_text(sample_article_model: ArticleModel) -> None:
    text = json.dumps(to_dict(sample_article_model))
    restored = from_dict(json.loads(text))
    assert restored == sample_article_model


def test_from_dict_rejects_missing_schema_version() -> None:
    with pytest.raises(ModelBuildError):
        from_dict({"article": {}})


def test_from_dict_rejects_unsupported_major_version(sample_article_model: ArticleModel) -> None:
    data = to_dict(sample_article_model)
    data["schema_version"] = "2.0.0"
    with pytest.raises(ModelBuildError):
        from_dict(data)


def test_from_dict_rejects_non_string_schema_version() -> None:
    with pytest.raises(ModelBuildError):
        from_dict({"schema_version": 1, "article": {}})


def test_schema_1_0_0_document_still_deserializes(sample_article_model: ArticleModel) -> None:
    # Simulates a real pre-Milestone-5C snapshot: none of the fields this
    # milestone added exist in the dict at all — not just null-valued,
    # genuinely absent, as an old checked-in JSON file would be.
    data = to_dict(sample_article_model)
    data["schema_version"] = "1.0.0"
    article = data["article"]
    for contributor in article["article_meta"]["contributors"]:
        del contributor["raw_contrib_type"]
        del contributor["full_name_raw"]
        del contributor["suffix"]
        del contributor["equal_contrib"]
        del contributor["credit_roles"]
    del article["article_meta"]["abstracts"]
    for scorecard in article["custom_meta"]["reviewer_scorecards"]:
        del scorecard["assigned_date"]
        del scorecard["due_date"]
        del scorecard["submitted_date"]

    restored = from_dict(data)

    assert restored.article_meta.abstracts == ()
    for contributor in restored.article_meta.contributors:
        assert contributor.raw_contrib_type is None
        assert contributor.full_name_raw is None
        assert contributor.suffix is None
        assert contributor.equal_contrib is False
        assert contributor.credit_roles == ()
    for scorecard in restored.custom_meta.reviewer_scorecards:
        assert scorecard.assigned_date is None
        assert scorecard.due_date is None
        assert scorecard.submitted_date is None


def test_empty_collections_round_trip(sample_article_model: ArticleModel) -> None:
    stripped_meta = replace(
        sample_article_model.article_meta,
        contributors=(),
        affiliations=(),
        corresponding_emails=(),
    )
    stripped = replace(
        sample_article_model, article_meta=stripped_meta, rounds=(), resolved_files=()
    )
    restored = from_dict(to_dict(stripped))
    assert restored == stripped
    assert isinstance(restored.article_meta, ArticleMeta)
