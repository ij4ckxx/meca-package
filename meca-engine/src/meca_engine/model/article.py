"""ArticleModel and every sub-object of the Internal Canonical Article Model.

Per 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §3.2-3.7, §4.1. This is the
one object graph every future generator (`generators.*`) will be
permitted to read — nothing here is derived from or aware of the source
XML's own structure; it represents the article's business content only.

Two deliberate, documented adaptations of the LLD's illustrative field
types (neither a redesign — both preserve every field the LLD names,
just choosing a hashable, immutable representation for it, consistent
with the rest of this codebase's established convention — see Milestone
4's ``JournalMetadata.issns: tuple[tuple[str | None, str], ...]`` for the
same precedent):

- Every LLD ``dict[str, str]``-typed field (``JournalMeta.abbrev_titles``,
  ``ReviewerScorecard.answers``) is instead ``tuple[tuple[str, str], ...]``
  — a plain ``dict`` field would make the containing frozen dataclass
  unhashable, defeating this milestone's "deterministic hashing" and
  "equality support" requirements.
- ``CustomMetaStore.form_answers`` (LLD: "open-vocabulary key ->
  tuple[str, ...]") is a small dedicated ``FormAnswerBag`` wrapper
  (ordered ``FormAnswerEntry`` tuples + a ``get()`` lookup helper) rather
  than a raw ``dict``, for the same hashability reason.

Every type is a frozen dataclass — write-once during construction (via
:class:`ArticleModelBuilder`), fully immutable once :meth:`ArticleModelBuilder.freeze`
returns an :class:`ArticleModel`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from meca_engine.exceptions import ModelBuildError
from meca_engine.model.enums import ContribType

if TYPE_CHECKING:
    from datetime import date, datetime

    from meca_engine.logging_.structured_logger import StructuredLogger
    from meca_engine.model.collections import (
        AffiliationList,
        ContributorList,
        FundingList,
        ResolvedFileList,
        RoundIndex,
    )
    from meca_engine.model.enums import (
        ActorRole,
        CorrespondenceChannel,
        CorrespondenceKind,
        ReviewOutcomeStatus,
    )
    from meca_engine.model.warnings import EngineWarning


# --- §3.2 identity / journal / article meta -------------------------------


@dataclass(frozen=True)
class ArticleIdentity:
    """Identifiers that name and locate one article, per 11_LLD_02... §3.2.

    Attributes:
        article_id: The exact input-folder string (BR-003).
        publisher_id_value: Verbatim ``article-id[@pub-id-type=publisher-id]`` (BR-080/136).
        doi_article_id_value: Verbatim ``article-id[@pub-id-type=doi]`` (BR-058 input).
        journal_id: Config lookup key (ADR-028).
        source_object_key: S3 key of the root XML, for traceability/logging.
    """

    article_id: str
    publisher_id_value: str
    doi_article_id_value: str
    journal_id: str
    source_object_key: str


@dataclass(frozen=True)
class JournalMeta:
    """Journal-level metadata, copied verbatim, per 11_LLD_02... §3.2.

    Attributes:
        journal_title: The journal's title.
        issn_ppub: The print ISSN, if the journal has one.
        issn_epub: The electronic ISSN, if the journal has one.
        publisher_name: The publisher's name.
        abbrev_titles: Every abbreviated-title value, paired with its
            source ``abbrev-type`` (ordered pairs — see module docstring
            for why this is not a ``dict``).
        journal_ids: Every ``journal-id`` value, paired with its source
            ``journal-id-type`` (e.g. ``"publisher-id"``, ``"nlm-ta"``) —
            distinct from :attr:`ArticleIdentity.journal_id`, which is
            only the single ``publisher-id`` value used for config
            lookup. Added Milestone 9 (journal-metadata completeness).
        volume: The journal volume this article was published in, if
            known. Added Milestone 9 — sourced from the same
            ``JournalMetadata`` extraction as the rest of this class,
            even though the underlying ``<volume>`` element lives under
            ``<article-meta>``, not ``<journal-meta>``.
        issue: The journal issue, if known.
        fpage: The first page, if known.
        lpage: The last page, if known.
    """

    journal_title: str
    issn_ppub: str | None
    issn_epub: str | None
    publisher_name: str
    abbrev_titles: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    journal_ids: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    volume: str | None = None
    issue: str | None = None
    fpage: str | None = None
    lpage: str | None = None


@dataclass(frozen=True)
class CorrespEmail:
    """One corresponding-author email, per 11_LLD_02... §3.3.

    Attributes:
        email: The email address.
        display_text: Trailing display text seen alongside the address in
            source samples (e.g. ``"Changchun, China"``), if present.
    """

    email: str
    display_text: str | None = None


@dataclass(frozen=True)
class Affiliation:
    """One affiliation, keyed by a model-internal integer, per 11_LLD_02... §3.3.

    Attributes:
        model_key: Stable within this :class:`ArticleModel` instance
            only — never derived from or equal to any source ``id``
            attribute (TC-060/070: article.xml strips all ids, so
            author<->affiliation linkage cannot depend on them).
        label: The affiliation's display label (e.g. ``"1"``), if the
            source separately tagged one.
        institution: The institution name (department joined in, when
            both are present, matching real reference-package style).
        city: The city, if present.
        state: The state/province, if present.
        country: The country, if present.
    """

    model_key: int
    institution: str
    label: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None


_EDITOR_CONTRIB_TYPES = frozenset(
    {
        ContribType.HANDLING_EDITOR,
        ContribType.ASSOCIATE_EDITOR,
        ContribType.ACADEMIC_EDITOR,
        ContribType.GUEST_EDITOR,
        ContribType.PRODUCTION_EDITOR,
        ContribType.COPY_EDITOR,
    }
)


@dataclass(frozen=True)
class Contributor:
    """One contributor, of any role, per 11_LLD_02... §3.3 (extended in Milestone 5C).

    A single, unified type for every contributor role
    (:class:`~meca_engine.model.enums.ContribType`) — never a separate
    subclass or parallel hierarchy per role, per the Architecture
    Review's explicit "unified contributor model with role-based
    behaviour" requirement. Role-specific fields below are simply
    ``None``/empty for roles they don't apply to (e.g. ``suffix`` is
    typically only populated for reviewer-role contributors in the 3
    real reference packages) — never a reason to split the type.

    Attributes:
        surname: The surname, if the source gave a structured
            surname/given-names split. Empty string when only an
            unsplit name was available — see ``full_name_raw``.
        given_names: The given name(s); same empty-string convention as
            ``surname``.
        contrib_type: This contributor's role.
        email: The contributor's own email, if present.
        orcid: The ORCID value only — never a source element id (BR-075).
        affiliation_keys: Model-internal keys into the article's
            ``AffiliationList`` — not source ids.
        is_corresponding: Whether this contributor is a corresponding
            author. Only meaningful for author-role contributors; a
            structural flag, not a role of its own (BR-130's
            "corresponding author" is an author who happens to be
            flagged this way, never a separate :class:`ContribType`
            member).
        raw_contrib_type: The verbatim source role string, preserved
            regardless of whether ``contrib_type`` resolved to a known
            member or to :attr:`~meca_engine.model.enums.ContribType.OTHER`
            — full traceability back to the source, per this project's
            established preserve-everything-verbatim convention.
        full_name_raw: The contributor's name as one unsplit string,
            when the source gave no separate surname/given-names split
            (confirmed on real data for reviewer and copy-editor
            identities, which arrive as a single name field, unlike
            authors' structured ``<name>`` elements). ``None`` when
            ``surname``/``given_names`` already hold the split form —
            never both populated, never a guessed split.
        suffix: An academic suffix (e.g. ``"PhD"``), if present.
        equal_contrib: Whether the source flagged this contributor as an
            equal contributor (JATS ``equal-contrib="yes"``).
        credit_roles: Every CRediT contribution-role label found for
            this contributor (e.g. ``"Conceptualization"``,
            ``"Writing – original draft"``), verbatim, in document
            order — an open vocabulary, never an enum.
        is_submitting_author: Whether the source flagged this contributor
            as the submitting author (``data-submitting-author="yes"``).
            Only meaningful for author-role contributors, same convention
            as ``is_corresponding``.
    """

    surname: str
    given_names: str
    contrib_type: ContribType
    email: str | None = None
    orcid: str | None = None
    affiliation_keys: tuple[int, ...] = field(default_factory=tuple)
    is_corresponding: bool = False
    raw_contrib_type: str | None = None
    full_name_raw: str | None = None
    suffix: str | None = None
    equal_contrib: bool = False
    credit_roles: tuple[str, ...] = field(default_factory=tuple)
    is_submitting_author: bool = False

    @property
    def is_author(self) -> bool:
        """Whether this contributor's role is author."""
        return self.contrib_type is ContribType.AUTHOR

    @property
    def is_reviewer(self) -> bool:
        """Whether this contributor's role is reviewer."""
        return self.contrib_type is ContribType.REVIEWER

    @property
    def is_editor(self) -> bool:
        """Whether this contributor's role is any of the editor-family roles."""
        return self.contrib_type in _EDITOR_CONTRIB_TYPES


@dataclass(frozen=True)
class ArticleCounts:
    """Structural counts copied from source ``<counts>``, per 11_LLD_02... §3.2.

    ``table_count``/``equation_count``/``page_count`` added Milestone 9
    (previously genuinely absent at every layer — extraction, model, and
    generator).
    """

    word_count: int | None = None
    ref_count: int | None = None
    fig_count: int | None = None
    table_count: int | None = None
    equation_count: int | None = None
    page_count: int | None = None


@dataclass(frozen=True)
class HistoryDates:
    """Article history dates, per 11_LLD_02... §3.2."""

    received: date | None = None
    revision: date | None = None
    accepted: date | None = None


@dataclass(frozen=True)
class Abstract:
    """One abstract section, per Milestone 5C (Architecture Review §6.11).

    JATS supports multiple ``<abstract>`` elements per article (e.g. a
    main abstract plus a ``trans-abstract``); this type represents one
    of them, generically. None of the 3 real reference packages exhibit
    more than one, or populate ``abstract_type``/``language`` — the
    generality here is for JATS-spec conformance, not evidenced by
    current real data.

    Attributes:
        text: The abstract's text content, flattened (inline markup not
            preserved — consistent with every other free-text ICAM
            field, e.g. ``article_title``).
        abstract_type: The verbatim source ``abstract-type`` attribute,
            if present (e.g. ``"graphical"``, ``"teaser"``).
        language: The verbatim source language attribute, if present —
            checked as both a plain ``lang`` attribute and an
            XML-namespace-qualified ``xml:lang`` attribute (mirroring
            ``ArticleMetadata.language``'s own Milestone 4 convention).
    """

    text: str
    abstract_type: str | None = None
    language: str | None = None


@dataclass(frozen=True)
class ArticleMeta:
    """Article-level metadata, per 11_LLD_02... §3.2 (extended in Milestone 5C).

    Attributes:
        display_channel_subject: e.g. ``"Review Article"`` — input to the
            (later) article-type mapping; unchanged by this milestone.
        heading_subjects: Every heading/subject value found.
        article_title: The article's title.
        abstracts: Every abstract section found, verbatim, in document
            order (Milestone 5C addition).
        contributors: Every contributor, of any role, ordered (display
            order preserved) — see :class:`Contributor`'s own docstring
            for the unified, role-based design.
        affiliations: Every affiliation.
        corresponding_emails: Ordered; index 0 is the primary
            corresponding email (BR-130 resolution rule — resolution
            itself is Milestone 5B's job; this model only holds the
            already-ordered result).
        copyright_statement: Verbatim copyright wording (BR-045/062 —
            never normalized).
        copyright_year: The copyright year, as source text.
        funding: Every funding statement, verbatim (BR-060's
            ``funding-group`` content, copied as plain strings).
        keywords: Every keyword, verbatim.
        counts: Structural counts.
        history_dates: Received/revision/accepted dates.
        pub_dates: Every publication date, paired with its source
            ``pub-type`` (e.g. ``"epub"``, ``"ppub"``), in document
            order. Added Milestone 9 (journal-metadata completeness).
    """

    display_channel_subject: str
    article_title: str
    contributors: ContributorList
    affiliations: AffiliationList
    corresponding_emails: tuple[CorrespEmail, ...] = field(default_factory=tuple)
    heading_subjects: tuple[str, ...] = field(default_factory=tuple)
    copyright_statement: str | None = None
    copyright_year: str | None = None
    funding: FundingList = field(default_factory=tuple)
    keywords: tuple[str, ...] = field(default_factory=tuple)
    counts: ArticleCounts = field(default_factory=ArticleCounts)
    history_dates: HistoryDates = field(default_factory=HistoryDates)
    abstracts: tuple[Abstract, ...] = field(default_factory=tuple)
    pub_dates: tuple[tuple[str, date], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class BodyFragment:
    """The article body, deliberately not decomposed further, per 11_LLD_02... §3.2.

    Attributes:
        raw_xml_fragment: The ``<body>`` subtree, copied verbatim
            byte-for-byte. raw.xml copies it verbatim (BR-043);
            article.xml never includes it at all (BR-072); no generator
            needs structured access to its internals, so it is never
            parsed back out of this string anywhere in the ICAM.
    """

    raw_xml_fragment: str


# --- §3.4 CustomMetaStore ---------------------------------------------------


@dataclass(frozen=True)
class FormAnswerEntry:
    """One open-vocabulary form-answer key and its (possibly multi-valued) answer(s)."""

    key: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class FormAnswerBag:
    """Every open-vocabulary custom-meta form answer, per 11_LLD_02... §3.4.

    A small ordered wrapper around ``tuple[FormAnswerEntry, ...]`` rather
    than a raw ``dict`` (see module docstring) — :meth:`get` provides the
    same by-key lookup a ``dict`` would.
    """

    entries: tuple[FormAnswerEntry, ...] = field(default_factory=tuple)

    def get(self, key: str) -> tuple[str, ...] | None:
        """Return the values for ``key``, or ``None`` if it is not present."""
        for entry in self.entries:
            if entry.key == key:
                return entry.values
        return None


@dataclass(frozen=True)
class FileEntry:
    """One file-category custom-meta record, per 11_LLD_02... §3.4.

    Attributes:
        round_label: e.g. ``"Original"``, ``"R1"`` — opaque string (ADR-014).
        category: Open vocabulary: ``"manuscript"``, ``"figure"``,
            ``"tables"``, ... (BR-019).
        original_filename: The declared original filename.
        declared_path_hint: The source ``path`` field — a hint only, not
            authoritative (BR-016/017).
        declared_size_bytes: The declared size, if present.
    """

    round_label: str
    category: str
    original_filename: str
    declared_path_hint: str
    declared_size_bytes: int | None = None


@dataclass(frozen=True)
class ReviewerScorecard:
    """One reviewer's scorecard for one round, per 11_LLD_02... §3.4 (extended in Milestone 5C).

    Attributes:
        round_label: The round this scorecard belongs to.
        reviewer_name: The reviewer's name.
        reviewer_email: The reviewer's email.
        answers: Every ``QN_*`` answer, as ordered
            ``(question_key, answer_text)`` pairs (BR-075 prefix-match;
            open-ended, never a fixed question list).
        overall_recommendation: The overall recommendation, if given.
        outcome_status: Whether this assignment completed/declined/etc.
        assigned_date: When the reviewer was assigned (BR-114), if a
            confirmed source field is found for it — see
            :mod:`meca_engine.extraction.custom_meta_classifier`'s
            module docstring for why this remains ``None`` on all 3
            real reference packages today: no per-review timestamp
            source was identified for reviewers who actually completed
            a review, and this field is never guessed or defaulted.
        due_date: When the review was due, same sourcing caveat.
        submitted_date: When the review was submitted, same sourcing
            caveat.
    """

    round_label: str
    reviewer_name: str
    reviewer_email: str
    outcome_status: ReviewOutcomeStatus
    answers: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    overall_recommendation: str | None = None
    assigned_date: date | None = None
    due_date: date | None = None
    submitted_date: date | None = None


@dataclass(frozen=True)
class DecisionDraft:
    """One round's editorial decision text, per 11_LLD_02... §3.4."""

    round_label: str
    decision_text: str
    editor_name: str | None = None
    associate_editor_name: str | None = None
    decision_date: date | None = None


@dataclass(frozen=True)
class DeclineReason:
    """One reviewer's decline/termination reason, per 11_LLD_02... §3.4.

    The LLD names this type (``decline_reasons: tuple[DeclineReason, ...]``)
    without detailing its fields; BR-068 ("article.xml custom-meta Drops
    reviewer-decline-reasons") confirms the source key is per-reviewer,
    per-round text — the fields below are this milestone's documented,
    non-blocking best-effort completion of that gap.
    """

    round_label: str
    reviewer_name: str
    reason_text: str


@dataclass(frozen=True)
class CorrespondenceEvent:
    """One workflow correspondence event, per 11_LLD_02... §3.4.

    Attributes:
        round_label: The round this event belongs to, if applicable.
        timestamp: When the event occurred.
        actor_name: Who performed the event.
        actor_role: The actor's role.
        channel: Who the event was visible to.
        text: The event's text content.
        attachment_url: An attachment link, if present (ADR-003).
        event_kind: What kind of event this is (ADR-005 scope).
    """

    timestamp: datetime
    actor_name: str
    actor_role: ActorRole
    channel: CorrespondenceChannel
    event_kind: CorrespondenceKind
    text: str
    round_label: str | None = None
    attachment_url: str | None = None


@dataclass(frozen=True)
class WorkflowLog:
    """Every workflow correspondence event, ordered chronologically, per 11_LLD_02... §3.4."""

    events: tuple[CorrespondenceEvent, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CustomMetaStore:
    """The audit-trail-of-record, per 11_LLD_02... §3.4.

    Built once by the (Milestone 5B) custom-meta classifier and never
    re-derived downstream — this milestone defines only the shape.
    """

    form_answers: FormAnswerBag = field(default_factory=FormAnswerBag)
    file_entries: tuple[FileEntry, ...] = field(default_factory=tuple)
    reviewer_scorecards: tuple[ReviewerScorecard, ...] = field(default_factory=tuple)
    decision_drafts: tuple[DecisionDraft, ...] = field(default_factory=tuple)
    decline_reasons: tuple[DeclineReason, ...] = field(default_factory=tuple)
    workflow_log: WorkflowLog = field(default_factory=WorkflowLog)


# --- §3.5 RoundIndex ---------------------------------------------------------


@dataclass(frozen=True)
class RoundInfo:
    """One submission round, per 11_LLD_02... §3.5.

    Attributes:
        label: Generic string (ADR-014).
        sequence_number: From ``vocab-identifier`` (BR-010).
        is_latest: ``True`` for exactly one ``RoundInfo`` in a given
            ``RoundIndex`` (enforced by :mod:`meca_engine.model.validation`,
            not by this type itself).
    """

    label: str
    sequence_number: int
    is_latest: bool


# --- §3.6 ResolvedFileList ----------------------------------------------------


@dataclass(frozen=True)
class ResolvedFile:
    """One file resolved to its physical staged location, per 11_LLD_02... §3.6."""

    round_label: str
    category: str
    original_filename: str
    staged_physical_path: str
    checksum: str
    size_bytes: int
    media_type: str


# --- §3.2 ArticleModel (root) -------------------------------------------------


@dataclass(frozen=True)
class ArticleModel:
    """The Internal Canonical Article Model — the one object every generator reads.

    Per 11_LLD_02... §3.1: no generator ever touches the staged Kriyadocs
    XML, a file path string, or the S3 client directly. Built exclusively
    via :class:`ArticleModelBuilder`; never constructed directly outside
    of tests (real construction always goes through the builder's
    write-once field discipline).

    Attributes:
        warnings: Specification deviations the engine recovered from
            without aborting generation (Milestone 10, ADR-032 — e.g. a
            filename derived from ``declared_path_hint`` when the
            source's own name field was missing). Empty for the common
            case where nothing was recovered from; unlike the 7 fields
            above, never mandatory — see :meth:`ArticleModelBuilder.set_warnings`.
    """

    identity: ArticleIdentity
    journal_meta: JournalMeta
    article_meta: ArticleMeta
    body_fragment: BodyFragment
    custom_meta: CustomMetaStore
    rounds: RoundIndex
    resolved_files: ResolvedFileList
    warnings: tuple[EngineWarning, ...] = field(default_factory=tuple)


# --- §3.7 / §4.1 ArticleModelBuilder ------------------------------------------
#
# ``None`` is the "not yet set" sentinel for every one of the 7 setters
# below — legitimate here (unlike a general-purpose ``_UNSET`` object)
# because all 7 fields are required, non-optional sub-objects on the
# frozen ``ArticleModel``: a real call to e.g. ``set_identity(None)``
# would be a caller bug that ``ArticleModel``'s own (non-Optional) field
# type immediately rejects at ``freeze()`` time via the missing-field
# check below, so no ambiguity between "unset" and "deliberately set to
# a null value" can arise in practice.


class ArticleModelBuilder:
    """Accumulates extracted data into a not-yet-frozen `ArticleModel`.

    Per 11_LLD_02... §4.1: enforces write-once field semantics (each
    field may be set exactly once) and produces the frozen instance via
    :meth:`freeze`. One instance per article; discarded after
    :meth:`freeze` is called. Depends on nothing beyond the foundation
    layer (:mod:`meca_engine.exceptions`, optionally
    :mod:`meca_engine.logging_` for the caller-supplied logger).
    """

    def __init__(self, article_id: str, *, logger: StructuredLogger | None = None) -> None:
        """Initialize a builder for one article.

        Args:
            article_id: The article this builder is accumulating a model
                for — used only for logging/error context, never stored
                on the frozen result beyond ``identity.article_id``
                (set separately via :meth:`set_identity`).
            logger: Optional structured logger. Model creation, freeze,
                and validation events are logged through it when given;
                entirely a no-op when omitted.
        """
        self._article_id = article_id
        self._logger = logger
        self._identity: ArticleIdentity | None = None
        self._journal_meta: JournalMeta | None = None
        self._article_meta: ArticleMeta | None = None
        self._body_fragment: BodyFragment | None = None
        self._custom_meta: CustomMetaStore | None = None
        self._rounds: RoundIndex | None = None
        self._resolved_files: ResolvedFileList | None = None
        self._warnings: tuple[EngineWarning, ...] | None = None
        if self._logger is not None:
            self._logger.info(
                "ArticleModelBuilder created",
                stage="model.article",
                context={"article_id": article_id},
            )

    def _assert_not_already_set(self, field_name: str, current_value: object) -> None:
        if current_value is not None:
            raise ModelBuildError(
                f"Field {field_name!r} was already set for article {self._article_id!r}",
                article_id=self._article_id,
                stage="model.article",
            )

    def set_identity(self, identity: ArticleIdentity) -> None:
        """Set the article's identity. May be called at most once."""
        self._assert_not_already_set("identity", self._identity)
        self._identity = identity

    def set_journal_meta(self, journal_meta: JournalMeta) -> None:
        """Set the article's journal metadata. May be called at most once."""
        self._assert_not_already_set("journal_meta", self._journal_meta)
        self._journal_meta = journal_meta

    def set_article_meta(self, article_meta: ArticleMeta) -> None:
        """Set the article's own metadata. May be called at most once."""
        self._assert_not_already_set("article_meta", self._article_meta)
        self._article_meta = article_meta

    def set_body_fragment(self, body_fragment: BodyFragment) -> None:
        """Set the article's body fragment. May be called at most once."""
        self._assert_not_already_set("body_fragment", self._body_fragment)
        self._body_fragment = body_fragment

    def set_custom_meta(self, store: CustomMetaStore) -> None:
        """Set the article's custom-metadata store. May be called at most once."""
        self._assert_not_already_set("custom_meta", self._custom_meta)
        self._custom_meta = store

    def set_rounds(self, index: RoundIndex) -> None:
        """Set the article's round index. May be called at most once."""
        self._assert_not_already_set("rounds", self._rounds)
        self._rounds = index

    def set_resolved_files(self, files: ResolvedFileList) -> None:
        """Set the article's resolved file list. May be called at most once."""
        self._assert_not_already_set("resolved_files", self._resolved_files)
        self._resolved_files = files

    def set_warnings(self, warnings: tuple[EngineWarning, ...]) -> None:
        """Set the article's recovered-specification-deviation warnings.

        Unlike the 7 setters above, this is optional — omitting the call
        entirely leaves :attr:`ArticleModel.warnings` empty, since most
        articles trigger no recoverable deviation at all. May still be
        called at most once, for the same write-once discipline as every
        other field.
        """
        self._assert_not_already_set("warnings", self._warnings)
        self._warnings = warnings

    def freeze(self) -> ArticleModel:
        """Produce the frozen `ArticleModel`.

        Returns:
            The immutable `ArticleModel`.

        Raises:
            ModelBuildError: If any required field has not been set.
        """
        missing = [
            name
            for name, value in (
                ("identity", self._identity),
                ("journal_meta", self._journal_meta),
                ("article_meta", self._article_meta),
                ("body_fragment", self._body_fragment),
                ("custom_meta", self._custom_meta),
                ("rounds", self._rounds),
                ("resolved_files", self._resolved_files),
            )
            if value is None
        ]
        if missing:
            raise ModelBuildError(
                f"Cannot freeze article {self._article_id!r}: missing required field(s) {missing}",
                article_id=self._article_id,
                stage="model.article",
            )
        assert self._identity is not None
        assert self._journal_meta is not None
        assert self._article_meta is not None
        assert self._body_fragment is not None
        assert self._custom_meta is not None
        assert self._rounds is not None
        assert self._resolved_files is not None
        model = ArticleModel(
            identity=self._identity,
            journal_meta=self._journal_meta,
            article_meta=self._article_meta,
            body_fragment=self._body_fragment,
            custom_meta=self._custom_meta,
            rounds=self._rounds,
            resolved_files=self._resolved_files,
            warnings=self._warnings or (),
        )
        if self._logger is not None:
            self._logger.info(
                "ArticleModel frozen",
                stage="model.article",
                context={
                    "article_id": self._article_id,
                    "contributor_count": len(model.article_meta.contributors),
                    "round_count": len(model.rounds),
                    "resolved_file_count": len(model.resolved_files),
                },
            )
        return model
