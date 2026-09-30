"""Unit tests for meca_engine.model.builders.

These Protocols carry no implementation — the only meaningful thing to
test is that they are structurally satisfied by the real classes they
preview/mirror, without any explicit inheritance declared (duck typing).
"""

from __future__ import annotations

import pytest

from meca_engine.model.article import ArticleModelBuilder
from meca_engine.model.builders import (
    ArticleBuilder,
    AssetBuilder,
    ContributorBuilder,
    JournalBuilder,
    WorkflowBuilder,
)

pytestmark = pytest.mark.unit


def test_article_model_builder_satisfies_article_builder_protocol(
    empty_builder: ArticleModelBuilder,
) -> None:
    assert isinstance(empty_builder, ArticleBuilder)


def test_article_model_builder_is_not_declared_to_inherit_from_article_builder() -> None:
    assert ArticleBuilder not in ArticleModelBuilder.__mro__


def test_protocols_are_not_instantiable_directly() -> None:
    for protocol in (ContributorBuilder, JournalBuilder, WorkflowBuilder, AssetBuilder):
        with pytest.raises(TypeError):
            protocol()  # type: ignore[misc]


def test_a_conforming_object_satisfies_contributor_builder_protocol() -> None:
    class _FakeContributorBuilder:
        def build(self, raw_contributor_data: object) -> tuple[object, ...]:
            return ()

    assert isinstance(_FakeContributorBuilder(), ContributorBuilder)


def test_a_non_conforming_object_does_not_satisfy_contributor_builder_protocol() -> None:
    class _NotABuilder:
        pass

    assert not isinstance(_NotABuilder(), ContributorBuilder)
