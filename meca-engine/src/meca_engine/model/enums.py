"""Enumerated types used throughout the Internal Canonical Article Model.

Per 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §3.3-3.4. Every enum here is a
closed, ICAM-internal vocabulary — never the source's own open-vocabulary
strings (those are preserved verbatim as plain ``str`` fields elsewhere,
e.g. ``CustomMetaStore.form_answers``). Matches the rest of the codebase's
``class X(str, Enum)`` convention (not ``enum.StrEnum``, Python 3.11+
only — see pyproject.toml's documented rationale).
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class ContribType(str, Enum):
    """A contributor's role within the ICAM's ``ContributorList``.

    Extended in Milestone 5C (Architecture Review finding §2.5/§6.1):
    direct inspection of the 3 real reference packages' ``article.xml``
    output showed ``contrib-group`` entries for roles beyond author
    (editors, associate editors, reviewers) — the single-member design
    from Milestone 5A undersized this enum. ``OTHER`` is the closed
    vocabulary's documented escape hatch for any future role this list
    doesn't yet name — paired with :attr:`~meca_engine.model.article.Contributor.raw_contrib_type`,
    which always preserves the verbatim source value regardless of which
    member it mapped to, so no role information is ever lost even when
    it collapses to ``OTHER``.
    """

    AUTHOR = "author"
    REVIEWER = "reviewer"
    HANDLING_EDITOR = "handling_editor"
    ASSOCIATE_EDITOR = "associate_editor"
    ACADEMIC_EDITOR = "academic_editor"
    GUEST_EDITOR = "guest_editor"
    PRODUCTION_EDITOR = "production_editor"
    COPY_EDITOR = "copy_editor"
    OTHER = "other"


@unique
class ReviewOutcomeStatus(str, Enum):
    """The outcome of one reviewer's assignment, per 11_LLD_02... §3.4."""

    COMPLETED = "completed"
    DECLINED = "declined"
    TERMINATED = "terminated"
    PENDING = "pending"


@unique
class ActorRole(str, Enum):
    """Who performed a workflow correspondence event, per 11_LLD_02... §3.4."""

    REVIEWER = "reviewer"
    EDITOR = "editor"
    ASSOCIATE_EDITOR = "associate_editor"
    AUTHOR = "author"
    PUBLISHER = "publisher"
    COPYEDITOR = "copyeditor"
    PREEDITOR = "preeditor"


@unique
class CorrespondenceChannel(str, Enum):
    """Who a workflow correspondence event was visible to, per 11_LLD_02... §3.4."""

    TO_AUTHOR = "to_author"
    TO_EDITOR_CONFIDENTIAL = "to_editor_confidential"
    INTERNAL = "internal"


@unique
class CorrespondenceKind(str, Enum):
    """What kind of workflow correspondence event this is, per 11_LLD_02... §3.4 (ADR-005 scope)."""

    REVIEW_COMMENT = "review_comment"
    SCREENING_QUERY = "screening_query"
    EDITOR_REASSIGNMENT = "editor_reassignment"
    AUTHOR_SUGGESTED_REVIEWER = "author_suggested_reviewer"
    PRODUCTION_QUERY = "production_query"
