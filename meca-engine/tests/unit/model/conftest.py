"""Shared fixtures for the Internal Canonical Article Model unit tests."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from meca_engine.model.article import (
    Abstract,
    Affiliation,
    ArticleCounts,
    ArticleIdentity,
    ArticleMeta,
    ArticleModel,
    ArticleModelBuilder,
    BodyFragment,
    Contributor,
    CorrespEmail,
    CorrespondenceEvent,
    CustomMetaStore,
    DecisionDraft,
    DeclineReason,
    FileEntry,
    FormAnswerBag,
    FormAnswerEntry,
    HistoryDates,
    JournalMeta,
    ResolvedFile,
    ReviewerScorecard,
    RoundInfo,
    WorkflowLog,
)
from meca_engine.model.enums import (
    ActorRole,
    ContribType,
    CorrespondenceChannel,
    CorrespondenceKind,
    ReviewOutcomeStatus,
)


def build_sample_article_model(article_id: str = "cs-2025-0001") -> ArticleModel:
    """Build a small, fully-populated, structurally-valid `ArticleModel`.

    Exercises every sub-object at least once, without going through
    `ArticleModelBuilder` (tests of the builder itself construct it via
    the builder directly) — a plain, direct construction fixture for
    every other test module that just needs *an* `ArticleModel`.
    """
    affiliation = Affiliation(model_key=1, institution="University of Example", country="USA")
    contributor = Contributor(
        surname="Doe",
        given_names="Jane",
        contrib_type=ContribType.AUTHOR,
        email="jane.doe@example.com",
        orcid="0000-0001-2345-6789",
        affiliation_keys=(1,),
        is_corresponding=True,
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
            abbrev_titles=(("publisher", "J. Ex."),),
        ),
        article_meta=ArticleMeta(
            display_channel_subject="Review Article",
            article_title="A Study of Example Practices",
            abstracts=(Abstract(text="This study examines example practices."),),
            contributors=(contributor,),
            affiliations=(affiliation,),
            corresponding_emails=(CorrespEmail(email="jane.doe@example.com"),),
            heading_subjects=("Cell Biology",),
            copyright_statement="© 2025 The Author(s).",
            copyright_year="2025",
            funding=("Example Foundation Grant 12345",),
            keywords=("examples", "testing"),
            counts=ArticleCounts(word_count=5000, ref_count=42, fig_count=3),
            history_dates=HistoryDates(
                received=date(2025, 1, 10),
                revision=date(2025, 2, 1),
                accepted=date(2025, 2, 20),
            ),
        ),
        body_fragment=BodyFragment(raw_xml_fragment="<body><p>Example content.</p></body>"),
        custom_meta=CustomMetaStore(
            form_answers=FormAnswerBag(
                entries=(FormAnswerEntry(key="Authorship", values=("Yes",)),)
            ),
            file_entries=(
                FileEntry(
                    round_label="Original",
                    category="manuscript",
                    original_filename="manuscript.docx",
                    declared_path_hint="/Original/manuscript.docx",
                    declared_size_bytes=102400,
                ),
            ),
            reviewer_scorecards=(
                ReviewerScorecard(
                    round_label="Original",
                    reviewer_name="Dr. Reviewer",
                    reviewer_email="reviewer@example.com",
                    outcome_status=ReviewOutcomeStatus.COMPLETED,
                    answers=(("QN_01", "Yes"),),
                    overall_recommendation="Minor Revision",
                ),
            ),
            decision_drafts=(
                DecisionDraft(
                    round_label="Original",
                    decision_text="Please revise per reviewer comments.",
                    editor_name="Dr. Editor",
                    decision_date=date(2025, 2, 15),
                ),
            ),
            decline_reasons=(
                DeclineReason(
                    round_label="Original",
                    reviewer_name="Dr. Declined",
                    reason_text="Conflict of interest.",
                ),
            ),
            workflow_log=WorkflowLog(
                events=(
                    CorrespondenceEvent(
                        timestamp=datetime(2025, 1, 10, tzinfo=timezone.utc),
                        actor_name="Dr. Editor",
                        actor_role=ActorRole.EDITOR,
                        channel=CorrespondenceChannel.TO_AUTHOR,
                        event_kind=CorrespondenceKind.REVIEW_COMMENT,
                        text="Manuscript received.",
                        round_label="Original",
                    ),
                )
            ),
        ),
        rounds=(
            RoundInfo(label="Original", sequence_number=1, is_latest=False),
            RoundInfo(label="R1", sequence_number=2, is_latest=True),
        ),
        resolved_files=(
            ResolvedFile(
                round_label="Original",
                category="manuscript",
                original_filename="manuscript.docx",
                staged_physical_path="/staged/Original/manuscript.docx",
                checksum="abc123",
                size_bytes=102400,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        ),
    )


@pytest.fixture
def sample_article_model() -> ArticleModel:
    """A small, fully-populated, structurally-valid `ArticleModel`."""
    return build_sample_article_model()


@pytest.fixture
def empty_builder() -> ArticleModelBuilder:
    """A fresh `ArticleModelBuilder` with nothing set yet."""
    return ArticleModelBuilder("cs-2025-0001")
