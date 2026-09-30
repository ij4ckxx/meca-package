"""Unit tests for meca_engine.model.article — domain model, immutability, builder."""

from __future__ import annotations

import dataclasses
from datetime import date

import pytest

from meca_engine.exceptions import ModelBuildError
from meca_engine.model.article import (
    Abstract,
    Affiliation,
    ArticleIdentity,
    ArticleMeta,
    ArticleModel,
    ArticleModelBuilder,
    BodyFragment,
    Contributor,
    ReviewerScorecard,
)
from meca_engine.model.enums import ContribType, ReviewOutcomeStatus

from .conftest import build_sample_article_model

pytestmark = pytest.mark.unit


# --- object creation ---------------------------------------------------------


def test_builds_a_complete_article_model(sample_article_model: ArticleModel) -> None:
    assert sample_article_model.identity.article_id == "cs-2025-0001"
    assert sample_article_model.article_meta.article_title == "A Study of Example Practices"
    assert len(sample_article_model.article_meta.contributors) == 1
    assert len(sample_article_model.rounds) == 2


def test_defaults_produce_empty_collections_not_none() -> None:
    identity = ArticleIdentity(
        article_id="x",
        publisher_id_value="x",
        doi_article_id_value="x",
        journal_id="x",
        source_object_key="x",
    )
    assert identity.article_id == "x"
    contributor = Contributor(surname="Doe", given_names="Jane", contrib_type=ContribType.AUTHOR)
    assert contributor.affiliation_keys == ()
    assert contributor.email is None
    assert contributor.is_corresponding is False


# --- immutability -------------------------------------------------------------


def test_article_model_is_frozen(sample_article_model: ArticleModel) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        sample_article_model.identity = sample_article_model.identity  # type: ignore[misc]


def test_nested_sub_object_is_frozen(sample_article_model: ArticleModel) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        sample_article_model.article_meta.article_title = "changed"  # type: ignore[misc]


def test_collections_are_tuples_not_lists(sample_article_model: ArticleModel) -> None:
    assert isinstance(sample_article_model.article_meta.contributors, tuple)
    assert isinstance(sample_article_model.rounds, tuple)
    assert isinstance(sample_article_model.resolved_files, tuple)


# --- equality / hashing --------------------------------------------------------


def test_equal_article_models_compare_equal() -> None:
    first = build_sample_article_model("cs-2025-0001")
    second = build_sample_article_model("cs-2025-0001")
    assert first == second


def test_different_article_ids_compare_unequal() -> None:
    first = build_sample_article_model("cs-2025-0001")
    second = build_sample_article_model("cs-2025-0002")
    assert first != second


def test_equal_article_models_hash_equal() -> None:
    first = build_sample_article_model("cs-2025-0001")
    second = build_sample_article_model("cs-2025-0001")
    assert hash(first) == hash(second)


def test_article_model_is_usable_as_a_dict_key(sample_article_model: ArticleModel) -> None:
    mapping = {sample_article_model: "ok"}
    assert mapping[sample_article_model] == "ok"


# --- ArticleModelBuilder: happy path -------------------------------------------


def test_builder_freeze_produces_equivalent_model(
    empty_builder: ArticleModelBuilder, sample_article_model: ArticleModel
) -> None:
    empty_builder.set_identity(sample_article_model.identity)
    empty_builder.set_journal_meta(sample_article_model.journal_meta)
    empty_builder.set_article_meta(sample_article_model.article_meta)
    empty_builder.set_body_fragment(sample_article_model.body_fragment)
    empty_builder.set_custom_meta(sample_article_model.custom_meta)
    empty_builder.set_rounds(sample_article_model.rounds)
    empty_builder.set_resolved_files(sample_article_model.resolved_files)

    result = empty_builder.freeze()

    assert result == sample_article_model


# --- ArticleModelBuilder: write-once enforcement -------------------------------


def test_setting_a_field_twice_raises_model_build_error(empty_builder: ArticleModelBuilder) -> None:
    identity = ArticleIdentity("a", "a", "a", "a", "a")
    empty_builder.set_identity(identity)
    with pytest.raises(ModelBuildError) as exc_info:
        empty_builder.set_identity(identity)
    assert exc_info.value.article_id == "cs-2025-0001"


@pytest.mark.parametrize(
    "setter_name",
    [
        "set_identity",
        "set_journal_meta",
        "set_article_meta",
        "set_body_fragment",
        "set_custom_meta",
        "set_rounds",
        "set_resolved_files",
    ],
)
def test_every_setter_enforces_write_once(
    empty_builder: ArticleModelBuilder, sample_article_model: ArticleModel, setter_name: str
) -> None:
    value_by_setter = {
        "set_identity": sample_article_model.identity,
        "set_journal_meta": sample_article_model.journal_meta,
        "set_article_meta": sample_article_model.article_meta,
        "set_body_fragment": sample_article_model.body_fragment,
        "set_custom_meta": sample_article_model.custom_meta,
        "set_rounds": sample_article_model.rounds,
        "set_resolved_files": sample_article_model.resolved_files,
    }
    setter = getattr(empty_builder, setter_name)
    setter(value_by_setter[setter_name])
    with pytest.raises(ModelBuildError):
        setter(value_by_setter[setter_name])


# --- ArticleModelBuilder: incomplete freeze ------------------------------------


def test_freeze_before_any_field_set_raises_model_build_error(
    empty_builder: ArticleModelBuilder,
) -> None:
    with pytest.raises(ModelBuildError) as exc_info:
        empty_builder.freeze()
    assert "identity" in str(exc_info.value)


def test_freeze_with_one_missing_field_reports_only_that_field(
    empty_builder: ArticleModelBuilder, sample_article_model: ArticleModel
) -> None:
    empty_builder.set_identity(sample_article_model.identity)
    empty_builder.set_journal_meta(sample_article_model.journal_meta)
    empty_builder.set_article_meta(sample_article_model.article_meta)
    empty_builder.set_body_fragment(sample_article_model.body_fragment)
    empty_builder.set_custom_meta(sample_article_model.custom_meta)
    empty_builder.set_rounds(sample_article_model.rounds)
    # resolved_files deliberately never set

    with pytest.raises(ModelBuildError) as exc_info:
        empty_builder.freeze()

    assert "resolved_files" in str(exc_info.value)
    assert "identity" not in str(exc_info.value)


# --- ArticleModelBuilder: warnings (Milestone 10, ADR-032) ---------------------


def test_warnings_default_to_empty_tuple_when_never_set(
    empty_builder: ArticleModelBuilder, sample_article_model: ArticleModel
) -> None:
    empty_builder.set_identity(sample_article_model.identity)
    empty_builder.set_journal_meta(sample_article_model.journal_meta)
    empty_builder.set_article_meta(sample_article_model.article_meta)
    empty_builder.set_body_fragment(sample_article_model.body_fragment)
    empty_builder.set_custom_meta(sample_article_model.custom_meta)
    empty_builder.set_rounds(sample_article_model.rounds)
    empty_builder.set_resolved_files(sample_article_model.resolved_files)

    result = empty_builder.freeze()

    assert result.warnings == ()


def test_set_warnings_populates_the_frozen_model(
    empty_builder: ArticleModelBuilder, sample_article_model: ArticleModel
) -> None:
    from meca_engine.model.warnings import (
        ConfidenceLevel,
        EngineWarning,
        FindingOrigin,
        WarningCategory,
        WarningSeverity,
    )

    warning = EngineWarning(
        code="BR013_FALLBACK_FILENAME_FROM_PATH",
        category=WarningCategory.SPECIFICATION_FALLBACK,
        severity=WarningSeverity.WARNING,
        origin=FindingOrigin.SOURCE_DATA_ISSUE,
        rule_id="BR-013",
        recovery_rule_id="RR-001",
        confidence=ConfidenceLevel.HIGH,
        message="Original filename missing.",
        article_id="cs-2025-0001",
        suggested_action=None,
        is_recovery=True,
    )
    empty_builder.set_identity(sample_article_model.identity)
    empty_builder.set_journal_meta(sample_article_model.journal_meta)
    empty_builder.set_article_meta(sample_article_model.article_meta)
    empty_builder.set_body_fragment(sample_article_model.body_fragment)
    empty_builder.set_custom_meta(sample_article_model.custom_meta)
    empty_builder.set_rounds(sample_article_model.rounds)
    empty_builder.set_resolved_files(sample_article_model.resolved_files)
    empty_builder.set_warnings((warning,))

    result = empty_builder.freeze()

    assert result.warnings == (warning,)


def test_set_warnings_enforces_write_once(empty_builder: ArticleModelBuilder) -> None:
    empty_builder.set_warnings(())
    with pytest.raises(ModelBuildError):
        empty_builder.set_warnings(())


def test_builder_logs_creation_and_freeze_events() -> None:
    import logging

    from meca_engine.logging_.structured_logger import StructuredLogger

    class _ListHandler(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.records: list[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    underlying = logging.getLogger("meca_engine.test.builder_logging")
    handler = _ListHandler()
    underlying.addHandler(handler)
    underlying.setLevel(logging.DEBUG)
    underlying.propagate = False

    logger = StructuredLogger("test.builder_logging")
    model = build_sample_article_model()
    builder = ArticleModelBuilder("cs-2025-0001", logger=logger)
    builder.set_identity(model.identity)
    builder.set_journal_meta(model.journal_meta)
    builder.set_article_meta(model.article_meta)
    builder.set_body_fragment(model.body_fragment)
    builder.set_custom_meta(model.custom_meta)
    builder.set_rounds(model.rounds)
    builder.set_resolved_files(model.resolved_files)
    builder.freeze()

    messages = [r.getMessage() for r in handler.records]
    assert any("created" in m for m in messages)
    assert any("frozen" in m for m in messages)
    underlying.removeHandler(handler)


# --- graph integrity: model-internal affiliation keys --------------------------


def test_affiliation_keys_are_model_internal_not_source_ids() -> None:
    affiliation = Affiliation(model_key=1, institution="Example University")
    contributor = Contributor(
        surname="Doe",
        given_names="Jane",
        contrib_type=ContribType.AUTHOR,
        affiliation_keys=(affiliation.model_key,),
    )
    assert contributor.affiliation_keys == (1,)


def test_body_fragment_holds_raw_xml_verbatim() -> None:
    fragment = BodyFragment(raw_xml_fragment="<body><p>Hi</p></body>")
    assert fragment.raw_xml_fragment == "<body><p>Hi</p></body>"


# --- FormAnswerBag -------------------------------------------------------------


def test_form_answer_bag_get_returns_values_for_known_key(
    sample_article_model: ArticleModel,
) -> None:
    bag = sample_article_model.custom_meta.form_answers
    assert bag.get("Authorship") == ("Yes",)


def test_form_answer_bag_get_returns_none_for_unknown_key(
    sample_article_model: ArticleModel,
) -> None:
    bag = sample_article_model.custom_meta.form_answers
    assert bag.get("does-not-exist") is None


# --- Contributor: unified, role-based model (Milestone 5C) --------------------


def test_new_contributor_fields_default_to_backward_compatible_values() -> None:
    contributor = Contributor(surname="Doe", given_names="Jane", contrib_type=ContribType.AUTHOR)

    assert contributor.raw_contrib_type is None
    assert contributor.full_name_raw is None
    assert contributor.suffix is None
    assert contributor.equal_contrib is False
    assert contributor.credit_roles == ()


def test_is_author_property() -> None:
    author = Contributor(surname="Doe", given_names="Jane", contrib_type=ContribType.AUTHOR)
    reviewer = Contributor(surname="", given_names="", contrib_type=ContribType.REVIEWER)

    assert author.is_author is True
    assert reviewer.is_author is False


def test_is_reviewer_property() -> None:
    reviewer = Contributor(surname="", given_names="", contrib_type=ContribType.REVIEWER)
    author = Contributor(surname="Doe", given_names="Jane", contrib_type=ContribType.AUTHOR)

    assert reviewer.is_reviewer is True
    assert author.is_reviewer is False


@pytest.mark.parametrize(
    "contrib_type",
    [
        ContribType.HANDLING_EDITOR,
        ContribType.ASSOCIATE_EDITOR,
        ContribType.ACADEMIC_EDITOR,
        ContribType.GUEST_EDITOR,
        ContribType.PRODUCTION_EDITOR,
        ContribType.COPY_EDITOR,
    ],
)
def test_is_editor_property_true_for_every_editor_role(contrib_type: ContribType) -> None:
    contributor = Contributor(surname="", given_names="", contrib_type=contrib_type)

    assert contributor.is_editor is True


@pytest.mark.parametrize(
    "contrib_type", [ContribType.AUTHOR, ContribType.REVIEWER, ContribType.OTHER]
)
def test_is_editor_property_false_for_non_editor_roles(contrib_type: ContribType) -> None:
    contributor = Contributor(surname="", given_names="", contrib_type=contrib_type)

    assert contributor.is_editor is False


def test_reviewer_contributor_uses_full_name_raw_not_split_name() -> None:
    contributor = Contributor(
        surname="",
        given_names="",
        contrib_type=ContribType.REVIEWER,
        full_name_raw="Xiao Yan",
        email="yanxiao0421@163.com",
        suffix="PhD",
        raw_contrib_type="reviewer",
    )

    assert contributor.full_name_raw == "Xiao Yan"
    assert contributor.surname == ""
    assert contributor.suffix == "PhD"


def test_author_credit_roles_and_equal_contrib_preserved_verbatim() -> None:
    contributor = Contributor(
        surname="Li",
        given_names="Chao",
        contrib_type=ContribType.AUTHOR,
        equal_contrib=True,
        credit_roles=("Conceptualization", "Writing – original draft"),
    )

    assert contributor.equal_contrib is True
    assert contributor.credit_roles == ("Conceptualization", "Writing – original draft")


def test_other_contrib_type_preserves_raw_source_string() -> None:
    contributor = Contributor(
        surname="Smith",
        given_names="Pat",
        contrib_type=ContribType.OTHER,
        raw_contrib_type="translator",
    )

    assert contributor.contrib_type is ContribType.OTHER
    assert contributor.raw_contrib_type == "translator"


# --- Abstract (Milestone 5C) ---------------------------------------------------


def test_abstract_holds_text_type_and_language() -> None:
    abstract = Abstract(text="This study investigates...", abstract_type="graphical", language="en")

    assert abstract.text == "This study investigates..."
    assert abstract.abstract_type == "graphical"
    assert abstract.language == "en"


def test_abstract_type_and_language_default_to_none() -> None:
    abstract = Abstract(text="Plain abstract text.")

    assert abstract.abstract_type is None
    assert abstract.language is None


def test_article_meta_abstracts_defaults_to_empty_tuple() -> None:
    article_meta = ArticleMeta(
        display_channel_subject="Research Article",
        article_title="Title",
        contributors=(),
        affiliations=(),
    )

    assert article_meta.abstracts == ()


def test_article_meta_supports_multiple_abstracts() -> None:
    abstracts = (
        Abstract(text="Main abstract."),
        Abstract(text="Graphical abstract.", abstract_type="graphical"),
    )
    article_meta = ArticleMeta(
        display_channel_subject="Research Article",
        article_title="Title",
        contributors=(),
        affiliations=(),
        abstracts=abstracts,
    )

    assert len(article_meta.abstracts) == 2
    assert article_meta.abstracts[1].abstract_type == "graphical"


# --- ReviewerScorecard workflow dates (Milestone 5C) ---------------------------


def test_reviewer_scorecard_new_date_fields_default_to_none() -> None:
    scorecard = ReviewerScorecard(
        round_label="Original",
        reviewer_name="Xiao Yan",
        reviewer_email="yanxiao0421@163.com",
        outcome_status=ReviewOutcomeStatus.COMPLETED,
    )

    assert scorecard.assigned_date is None
    assert scorecard.due_date is None
    assert scorecard.submitted_date is None


def test_reviewer_scorecard_new_date_fields_hold_real_dates() -> None:
    scorecard = ReviewerScorecard(
        round_label="Original",
        reviewer_name="Xiao Yan",
        reviewer_email="yanxiao0421@163.com",
        outcome_status=ReviewOutcomeStatus.COMPLETED,
        assigned_date=date(2025, 5, 25),
        due_date=date(2025, 6, 4),
        submitted_date=date(2025, 5, 29),
    )

    assert scorecard.assigned_date == date(2025, 5, 25)
    assert scorecard.due_date == date(2025, 6, 4)
    assert scorecard.submitted_date == date(2025, 5, 29)
