"""Shared fixtures for RawXmlGenerator unit tests."""

from __future__ import annotations

from datetime import date

import pytest

from meca_engine.config.schema import (
    FeatureFlagsConfig,
    JournalConfig,
    NamespaceConfig,
    PublisherConfig,
    RawXmlConfig,
    RuntimeConfig,
)
from meca_engine.generators.context import GeneratorContext
from meca_engine.generators.diagnostics import DiagnosticsCollector
from meca_engine.generators.raw_xml.generator import RawXmlGenerator
from meca_engine.generators.xml.namespaces import NamespaceManager
from meca_engine.logging_.structured_logger import get_logger
from meca_engine.model.article import (
    Abstract,
    Affiliation,
    ArticleCounts,
    ArticleIdentity,
    ArticleMeta,
    ArticleModel,
    BodyFragment,
    Contributor,
    CorrespEmail,
    CustomMetaStore,
    DecisionDraft,
    DeclineReason,
    FileEntry,
    FormAnswerBag,
    FormAnswerEntry,
    HistoryDates,
    JournalMeta,
    ReviewerScorecard,
)
from meca_engine.model.enums import ContribType, ReviewOutcomeStatus

_NAMESPACE_REGISTRY = {
    "mml": "http://www.w3.org/1998/Math/MathML",
    "xlink": "http://www.w3.org/1999/xlink",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "ali": "http://www.niso.org/schemas/ali/1.0/",
}


@pytest.fixture
def namespace_config() -> NamespaceConfig:
    return NamespaceConfig(namespaces=_NAMESPACE_REGISTRY)


@pytest.fixture
def namespace_manager(namespace_config: NamespaceConfig) -> NamespaceManager:
    return NamespaceManager(namespace_config.namespaces)


@pytest.fixture
def raw_xml_config() -> RawXmlConfig:
    return RawXmlConfig(
        doctype_public_id="-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.3 20210610//EN",
        doctype_system_id="JATS-journalpublishing1-3.dtd",
        article_type="research-article",
        dtd_version="1.3",
        default_xml_lang="en",
        encoding="UTF-8",
        namespace_prefixes=("mml", "xlink", "xsi", "ali"),
        pretty_indent_spaces=0,
    )


@pytest.fixture
def raw_xml_generator(
    namespace_manager: NamespaceManager, raw_xml_config: RawXmlConfig
) -> RawXmlGenerator:
    return RawXmlGenerator(namespace_manager=namespace_manager, raw_xml_config=raw_xml_config)


def build_rich_article_model(article_id: str = "cs-2025-0001") -> ArticleModel:
    """Build an `ArticleModel` exercising every raw.xml-relevant ICAM field at least once."""
    author = Contributor(
        surname="Doe",
        given_names="Jane",
        contrib_type=ContribType.AUTHOR,
        email="jane.doe@example.com",
        orcid="0000-0001-2345-6789",
        affiliation_keys=(1,),
        is_corresponding=True,
        equal_contrib=True,
    )
    co_author = Contributor(
        surname="Smith",
        given_names="John",
        contrib_type=ContribType.AUTHOR,
        affiliation_keys=(2,),
        suffix="PhD",
    )
    reviewer = Contributor(
        surname="",
        given_names="",
        contrib_type=ContribType.REVIEWER,
        email="reviewer@example.com",
        full_name_raw="Alex Reviewer",
        raw_contrib_type="reviewer",
    )
    return ArticleModel(
        identity=ArticleIdentity(
            article_id=article_id,
            publisher_id_value="EX-2025-001",
            doi_article_id_value="EX-2025-001",
            journal_id="clinical-science",
            source_object_key=f"{article_id}/{article_id}.xml",
        ),
        journal_meta=JournalMeta(
            journal_title="Journal of Examples",
            issn_ppub="1234-5678",
            issn_epub="8765-4321",
            publisher_name="Example Press",
            abbrev_titles=(("pubmed", "J. Ex."),),
            journal_ids=(("nlm-ta", "j-ex"),),
            volume="12",
            issue="3",
            fpage="100",
            lpage="120",
        ),
        article_meta=ArticleMeta(
            display_channel_subject="Research Article",
            article_title="A Study of Example Practices",
            contributors=(author, co_author, reviewer),
            affiliations=(
                Affiliation(model_key=1, institution="University of Example", country="USA"),
                Affiliation(model_key=2, institution="Example Institute", country="UK"),
            ),
            corresponding_emails=(CorrespEmail(email="jane.doe@example.com"),),
            heading_subjects=("Cell Biology",),
            copyright_statement="© 2025 The Author(s).",
            copyright_year="2025",
            funding=("Example Foundation Grant 12345",),
            keywords=("examples", "testing"),
            counts=ArticleCounts(word_count=5000, ref_count=42, fig_count=3),
            history_dates=HistoryDates(
                received=date(2025, 1, 10), revision=date(2025, 2, 1), accepted=date(2025, 2, 20)
            ),
            abstracts=(Abstract(text="This study examines example practices."),),
            pub_dates=(("epub", date(2025, 3, 1)), ("ppub", date(2025, 3, 15))),
        ),
        body_fragment=BodyFragment(
            raw_xml_fragment=(
                '<body id="b1"><title>Example Title Page</title>'
                '<p id="p1">Abstract text.</p></body>'
            )
        ),
        custom_meta=CustomMetaStore(
            form_answers=FormAnswerBag(
                entries=(FormAnswerEntry(key="Authorship", values=("Yes",)),)
            ),
            file_entries=(
                FileEntry(
                    round_label="Original",
                    category="manuscript",
                    original_filename="manuscript.docx",
                    declared_path_hint="Original/manuscript.docx",
                    declared_size_bytes=1024,
                ),
            ),
            reviewer_scorecards=(
                ReviewerScorecard(
                    round_label="Original",
                    reviewer_name="Alex Reviewer",
                    reviewer_email="reviewer@example.com",
                    outcome_status=ReviewOutcomeStatus.COMPLETED,
                    overall_recommendation="Minor revisions",
                ),
            ),
            decision_drafts=(
                DecisionDraft(round_label="Original", decision_text="Send for minor revisions."),
            ),
            decline_reasons=(
                DeclineReason(
                    round_label="Original", reviewer_name="Sam Decliner", reason_text="Busy"
                ),
            ),
        ),
        rounds=(),
        resolved_files=(),
    )


@pytest.fixture
def rich_context(
    minimal_journal_config: JournalConfig,
    minimal_publisher_config: PublisherConfig,
    minimal_runtime_config: RuntimeConfig,
    minimal_feature_flags: FeatureFlagsConfig,
) -> GeneratorContext:
    return GeneratorContext(
        model=build_rich_article_model(),
        runtime_config=minimal_runtime_config,
        journal_config=minimal_journal_config,
        publisher_config=minimal_publisher_config,
        feature_flags=minimal_feature_flags,
        logger=get_logger("test.raw_xml"),
        diagnostics=DiagnosticsCollector(),
    )


@pytest.fixture
def empty_context(
    minimal_journal_config: JournalConfig,
    minimal_publisher_config: PublisherConfig,
    minimal_runtime_config: RuntimeConfig,
    minimal_feature_flags: FeatureFlagsConfig,
) -> GeneratorContext:
    return GeneratorContext(
        model=build_empty_article_model(),
        runtime_config=minimal_runtime_config,
        journal_config=minimal_journal_config,
        publisher_config=minimal_publisher_config,
        feature_flags=minimal_feature_flags,
        logger=get_logger("test.raw_xml"),
        diagnostics=DiagnosticsCollector(),
    )


def build_empty_article_model(article_id: str = "cs-2025-0002") -> ArticleModel:
    """Build the smallest structurally-valid `ArticleModel` — every optional field empty."""
    return ArticleModel(
        identity=ArticleIdentity(
            article_id=article_id,
            publisher_id_value="",
            doi_article_id_value="",
            journal_id="",
            source_object_key=f"{article_id}/{article_id}.xml",
        ),
        journal_meta=JournalMeta(
            journal_title="", issn_ppub=None, issn_epub=None, publisher_name=""
        ),
        article_meta=ArticleMeta(
            display_channel_subject="", article_title="Untitled", contributors=(), affiliations=()
        ),
        body_fragment=BodyFragment(raw_xml_fragment=""),
        custom_meta=CustomMetaStore(),
        rounds=(),
        resolved_files=(),
    )
