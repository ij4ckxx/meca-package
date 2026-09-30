"""JSON serialization / deserialization for the Internal Canonical Article Model.

Not part of 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md's own text (the LLD is
silent on a JSON representation) — added per this milestone's explicit
"Serialization" requirement. Orthogonal to the ICAM's role as generator
input: nothing here is read by any generator; it exists for tooling
(golden-baseline snapshots, debugging, cross-process transport) only. No
XML serialization is provided, per the current task's explicit scope.

**Versioning strategy**: every serialized document carries a top-level
``schema_version`` field (:data:`SCHEMA_VERSION`, semantic-versioned,
independent of the package's own version). :func:`from_dict` rejects an
unrecognized major version outright (a breaking schema change) and is the
one place a future minor-version migration shim would be added. A
document's fields are read by name (never by position), so an old
document with a since-added optional field simply gets that field's
default value back — demonstrated for real in Milestone 5C: every
Milestone-5C-added field (``Contributor.raw_contrib_type``/``full_name_raw``/
``suffix``/``equal_contrib``/``credit_roles``, ``ReviewerScorecard.assigned_date``/
``due_date``/``submitted_date``, ``ArticleMeta.abstracts``) is read via
``Mapping.get(key, default)`` rather than ``data[key]`` in every
``_*_from_dict`` function below, specifically so a schema-1.0.0 document
(pre-Milestone-5C) still deserializes correctly under schema 1.1.0 — the
minor-version bump this milestone made. Pre-existing fields keep the
stricter ``data[key]`` form, unchanged, since they were always required.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from meca_engine.exceptions import ModelBuildError
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

if TYPE_CHECKING:
    from collections.abc import Mapping

#: The ICAM JSON schema version this module reads and writes.
SCHEMA_VERSION = "1.1.0"

_SUPPORTED_MAJOR_VERSION = "1"


def _date_to_str(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _str_to_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value is not None else None


def _datetime_to_str(value: datetime) -> str:
    return value.isoformat()


def _str_to_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def to_dict(article: ArticleModel) -> dict[str, Any]:
    """Serialize an `ArticleModel` into a JSON-safe, versioned dict.

    Args:
        article: The frozen model to serialize.

    Returns:
        A dict with a top-level ``schema_version`` field and an
        ``article`` field holding the full object graph.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "article": {
            "identity": _identity_to_dict(article.identity),
            "journal_meta": _journal_meta_to_dict(article.journal_meta),
            "article_meta": _article_meta_to_dict(article.article_meta),
            "body_fragment": {"raw_xml_fragment": article.body_fragment.raw_xml_fragment},
            "custom_meta": _custom_meta_to_dict(article.custom_meta),
            "rounds": [_round_info_to_dict(r) for r in article.rounds],
            "resolved_files": [_resolved_file_to_dict(f) for f in article.resolved_files],
        },
    }


def from_dict(data: Mapping[str, Any]) -> ArticleModel:
    """Deserialize a JSON-safe dict (as produced by :func:`to_dict`) into an `ArticleModel`.

    Args:
        data: A dict previously produced by :func:`to_dict`.

    Returns:
        The reconstructed `ArticleModel`.

    Raises:
        ModelBuildError: If ``schema_version`` is missing or its major
            version is not one this module supports.
    """
    schema_version = data.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version.startswith(
        f"{_SUPPORTED_MAJOR_VERSION}."
    ):
        raise ModelBuildError(
            f"Unsupported or missing ICAM schema_version: {schema_version!r} "
            f"(expected major version {_SUPPORTED_MAJOR_VERSION!r})",
            stage="model.serialization",
        )
    article = data["article"]
    return ArticleModel(
        identity=_identity_from_dict(article["identity"]),
        journal_meta=_journal_meta_from_dict(article["journal_meta"]),
        article_meta=_article_meta_from_dict(article["article_meta"]),
        body_fragment=BodyFragment(raw_xml_fragment=article["body_fragment"]["raw_xml_fragment"]),
        custom_meta=_custom_meta_from_dict(article["custom_meta"]),
        rounds=tuple(_round_info_from_dict(r) for r in article["rounds"]),
        resolved_files=tuple(_resolved_file_from_dict(f) for f in article["resolved_files"]),
    )


# --- identity / journal / article meta --------------------------------------


def _identity_to_dict(identity: ArticleIdentity) -> dict[str, Any]:
    return {
        "article_id": identity.article_id,
        "publisher_id_value": identity.publisher_id_value,
        "doi_article_id_value": identity.doi_article_id_value,
        "journal_id": identity.journal_id,
        "source_object_key": identity.source_object_key,
    }


def _identity_from_dict(data: Mapping[str, Any]) -> ArticleIdentity:
    return ArticleIdentity(
        article_id=data["article_id"],
        publisher_id_value=data["publisher_id_value"],
        doi_article_id_value=data["doi_article_id_value"],
        journal_id=data["journal_id"],
        source_object_key=data["source_object_key"],
    )


def _journal_meta_to_dict(journal_meta: JournalMeta) -> dict[str, Any]:
    return {
        "journal_title": journal_meta.journal_title,
        "issn_ppub": journal_meta.issn_ppub,
        "issn_epub": journal_meta.issn_epub,
        "publisher_name": journal_meta.publisher_name,
        "abbrev_titles": [list(pair) for pair in journal_meta.abbrev_titles],
    }


def _journal_meta_from_dict(data: Mapping[str, Any]) -> JournalMeta:
    return JournalMeta(
        journal_title=data["journal_title"],
        issn_ppub=data["issn_ppub"],
        issn_epub=data["issn_epub"],
        publisher_name=data["publisher_name"],
        abbrev_titles=tuple((pair[0], pair[1]) for pair in data["abbrev_titles"]),
    )


def _contributor_to_dict(contributor: Contributor) -> dict[str, Any]:
    return {
        "surname": contributor.surname,
        "given_names": contributor.given_names,
        "contrib_type": contributor.contrib_type.value,
        "email": contributor.email,
        "orcid": contributor.orcid,
        "affiliation_keys": list(contributor.affiliation_keys),
        "is_corresponding": contributor.is_corresponding,
        "raw_contrib_type": contributor.raw_contrib_type,
        "full_name_raw": contributor.full_name_raw,
        "suffix": contributor.suffix,
        "equal_contrib": contributor.equal_contrib,
        "credit_roles": list(contributor.credit_roles),
    }


def _contributor_from_dict(data: Mapping[str, Any]) -> Contributor:
    return Contributor(
        surname=data["surname"],
        given_names=data["given_names"],
        contrib_type=ContribType(data["contrib_type"]),
        email=data["email"],
        orcid=data["orcid"],
        affiliation_keys=tuple(data["affiliation_keys"]),
        is_corresponding=data["is_corresponding"],
        raw_contrib_type=data.get("raw_contrib_type"),
        full_name_raw=data.get("full_name_raw"),
        suffix=data.get("suffix"),
        equal_contrib=data.get("equal_contrib", False),
        credit_roles=tuple(data.get("credit_roles", ())),
    )


def _affiliation_to_dict(affiliation: Affiliation) -> dict[str, Any]:
    return {
        "model_key": affiliation.model_key,
        "institution": affiliation.institution,
        "country": affiliation.country,
    }


def _affiliation_from_dict(data: Mapping[str, Any]) -> Affiliation:
    return Affiliation(
        model_key=data["model_key"], institution=data["institution"], country=data["country"]
    )


def _abstract_to_dict(abstract: Abstract) -> dict[str, Any]:
    return {
        "text": abstract.text,
        "abstract_type": abstract.abstract_type,
        "language": abstract.language,
    }


def _abstract_from_dict(data: Mapping[str, Any]) -> Abstract:
    return Abstract(
        text=data["text"],
        abstract_type=data.get("abstract_type"),
        language=data.get("language"),
    )


def _article_meta_to_dict(article_meta: ArticleMeta) -> dict[str, Any]:
    return {
        "display_channel_subject": article_meta.display_channel_subject,
        "article_title": article_meta.article_title,
        "abstracts": [_abstract_to_dict(a) for a in article_meta.abstracts],
        "contributors": [_contributor_to_dict(c) for c in article_meta.contributors],
        "affiliations": [_affiliation_to_dict(a) for a in article_meta.affiliations],
        "corresponding_emails": [
            {"email": e.email, "display_text": e.display_text}
            for e in article_meta.corresponding_emails
        ],
        "heading_subjects": list(article_meta.heading_subjects),
        "copyright_statement": article_meta.copyright_statement,
        "copyright_year": article_meta.copyright_year,
        "funding": list(article_meta.funding),
        "keywords": list(article_meta.keywords),
        "counts": {
            "word_count": article_meta.counts.word_count,
            "ref_count": article_meta.counts.ref_count,
            "fig_count": article_meta.counts.fig_count,
        },
        "history_dates": {
            "received": _date_to_str(article_meta.history_dates.received),
            "revision": _date_to_str(article_meta.history_dates.revision),
            "accepted": _date_to_str(article_meta.history_dates.accepted),
        },
    }


def _article_meta_from_dict(data: Mapping[str, Any]) -> ArticleMeta:
    counts = data["counts"]
    history = data["history_dates"]
    return ArticleMeta(
        display_channel_subject=data["display_channel_subject"],
        article_title=data["article_title"],
        abstracts=tuple(_abstract_from_dict(a) for a in data.get("abstracts", ())),
        contributors=tuple(_contributor_from_dict(c) for c in data["contributors"]),
        affiliations=tuple(_affiliation_from_dict(a) for a in data["affiliations"]),
        corresponding_emails=tuple(
            CorrespEmail(email=e["email"], display_text=e["display_text"])
            for e in data["corresponding_emails"]
        ),
        heading_subjects=tuple(data["heading_subjects"]),
        copyright_statement=data["copyright_statement"],
        copyright_year=data["copyright_year"],
        funding=tuple(data["funding"]),
        keywords=tuple(data["keywords"]),
        counts=ArticleCounts(
            word_count=counts["word_count"],
            ref_count=counts["ref_count"],
            fig_count=counts["fig_count"],
        ),
        history_dates=HistoryDates(
            received=_str_to_date(history["received"]),
            revision=_str_to_date(history["revision"]),
            accepted=_str_to_date(history["accepted"]),
        ),
    )


# --- custom meta store --------------------------------------------------------


def _form_answers_to_dict(bag: FormAnswerBag) -> list[dict[str, Any]]:
    return [{"key": e.key, "values": list(e.values)} for e in bag.entries]


def _form_answers_from_dict(data: list[Any]) -> FormAnswerBag:
    return FormAnswerBag(
        entries=tuple(FormAnswerEntry(key=e["key"], values=tuple(e["values"])) for e in data)
    )


def _file_entry_to_dict(entry: FileEntry) -> dict[str, Any]:
    return {
        "round_label": entry.round_label,
        "category": entry.category,
        "original_filename": entry.original_filename,
        "declared_path_hint": entry.declared_path_hint,
        "declared_size_bytes": entry.declared_size_bytes,
    }


def _file_entry_from_dict(data: Mapping[str, Any]) -> FileEntry:
    return FileEntry(
        round_label=data["round_label"],
        category=data["category"],
        original_filename=data["original_filename"],
        declared_path_hint=data["declared_path_hint"],
        declared_size_bytes=data["declared_size_bytes"],
    )


def _reviewer_scorecard_to_dict(scorecard: ReviewerScorecard) -> dict[str, Any]:
    return {
        "round_label": scorecard.round_label,
        "reviewer_name": scorecard.reviewer_name,
        "reviewer_email": scorecard.reviewer_email,
        "outcome_status": scorecard.outcome_status.value,
        "answers": [list(pair) for pair in scorecard.answers],
        "overall_recommendation": scorecard.overall_recommendation,
        "assigned_date": _date_to_str(scorecard.assigned_date),
        "due_date": _date_to_str(scorecard.due_date),
        "submitted_date": _date_to_str(scorecard.submitted_date),
    }


def _reviewer_scorecard_from_dict(data: Mapping[str, Any]) -> ReviewerScorecard:
    return ReviewerScorecard(
        round_label=data["round_label"],
        reviewer_name=data["reviewer_name"],
        reviewer_email=data["reviewer_email"],
        outcome_status=ReviewOutcomeStatus(data["outcome_status"]),
        answers=tuple((pair[0], pair[1]) for pair in data["answers"]),
        overall_recommendation=data["overall_recommendation"],
        assigned_date=_str_to_date(data.get("assigned_date")),
        due_date=_str_to_date(data.get("due_date")),
        submitted_date=_str_to_date(data.get("submitted_date")),
    )


def _decision_draft_to_dict(draft: DecisionDraft) -> dict[str, Any]:
    return {
        "round_label": draft.round_label,
        "decision_text": draft.decision_text,
        "editor_name": draft.editor_name,
        "associate_editor_name": draft.associate_editor_name,
        "decision_date": _date_to_str(draft.decision_date),
    }


def _decision_draft_from_dict(data: Mapping[str, Any]) -> DecisionDraft:
    return DecisionDraft(
        round_label=data["round_label"],
        decision_text=data["decision_text"],
        editor_name=data["editor_name"],
        associate_editor_name=data["associate_editor_name"],
        decision_date=_str_to_date(data["decision_date"]),
    )


def _decline_reason_to_dict(reason: DeclineReason) -> dict[str, Any]:
    return {
        "round_label": reason.round_label,
        "reviewer_name": reason.reviewer_name,
        "reason_text": reason.reason_text,
    }


def _decline_reason_from_dict(data: Mapping[str, Any]) -> DeclineReason:
    return DeclineReason(
        round_label=data["round_label"],
        reviewer_name=data["reviewer_name"],
        reason_text=data["reason_text"],
    )


def _correspondence_event_to_dict(event: CorrespondenceEvent) -> dict[str, Any]:
    return {
        "round_label": event.round_label,
        "timestamp": _datetime_to_str(event.timestamp),
        "actor_name": event.actor_name,
        "actor_role": event.actor_role.value,
        "channel": event.channel.value,
        "event_kind": event.event_kind.value,
        "text": event.text,
        "attachment_url": event.attachment_url,
    }


def _correspondence_event_from_dict(data: Mapping[str, Any]) -> CorrespondenceEvent:
    return CorrespondenceEvent(
        round_label=data["round_label"],
        timestamp=_str_to_datetime(data["timestamp"]),
        actor_name=data["actor_name"],
        actor_role=ActorRole(data["actor_role"]),
        channel=CorrespondenceChannel(data["channel"]),
        event_kind=CorrespondenceKind(data["event_kind"]),
        text=data["text"],
        attachment_url=data["attachment_url"],
    )


def _custom_meta_to_dict(store: CustomMetaStore) -> dict[str, Any]:
    return {
        "form_answers": _form_answers_to_dict(store.form_answers),
        "file_entries": [_file_entry_to_dict(e) for e in store.file_entries],
        "reviewer_scorecards": [_reviewer_scorecard_to_dict(s) for s in store.reviewer_scorecards],
        "decision_drafts": [_decision_draft_to_dict(d) for d in store.decision_drafts],
        "decline_reasons": [_decline_reason_to_dict(r) for r in store.decline_reasons],
        "workflow_log": {
            "events": [_correspondence_event_to_dict(e) for e in store.workflow_log.events]
        },
    }


def _custom_meta_from_dict(data: Mapping[str, Any]) -> CustomMetaStore:
    return CustomMetaStore(
        form_answers=_form_answers_from_dict(data["form_answers"]),
        file_entries=tuple(_file_entry_from_dict(e) for e in data["file_entries"]),
        reviewer_scorecards=tuple(
            _reviewer_scorecard_from_dict(s) for s in data["reviewer_scorecards"]
        ),
        decision_drafts=tuple(_decision_draft_from_dict(d) for d in data["decision_drafts"]),
        decline_reasons=tuple(_decline_reason_from_dict(r) for r in data["decline_reasons"]),
        workflow_log=WorkflowLog(
            events=tuple(_correspondence_event_from_dict(e) for e in data["workflow_log"]["events"])
        ),
    )


# --- rounds / resolved files ---------------------------------------------------


def _round_info_to_dict(round_info: RoundInfo) -> dict[str, Any]:
    return {
        "label": round_info.label,
        "sequence_number": round_info.sequence_number,
        "is_latest": round_info.is_latest,
    }


def _round_info_from_dict(data: Mapping[str, Any]) -> RoundInfo:
    return RoundInfo(
        label=data["label"],
        sequence_number=data["sequence_number"],
        is_latest=data["is_latest"],
    )


def _resolved_file_to_dict(resolved_file: ResolvedFile) -> dict[str, Any]:
    return {
        "round_label": resolved_file.round_label,
        "category": resolved_file.category,
        "original_filename": resolved_file.original_filename,
        "staged_physical_path": resolved_file.staged_physical_path,
        "checksum": resolved_file.checksum,
        "size_bytes": resolved_file.size_bytes,
        "media_type": resolved_file.media_type,
    }


def _resolved_file_from_dict(data: Mapping[str, Any]) -> ResolvedFile:
    return ResolvedFile(
        round_label=data["round_label"],
        category=data["category"],
        original_filename=data["original_filename"],
        staged_physical_path=data["staged_physical_path"],
        checksum=data["checksum"],
        size_bytes=data["size_bytes"],
        media_type=data["media_type"],
    )
