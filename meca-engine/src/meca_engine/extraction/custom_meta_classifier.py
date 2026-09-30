"""Custom-metadata classification — Milestone 5B (11_LLD_02... §4.3).

Classifies Milestone 4's flat, unfiltered
:class:`~meca_engine.extraction.metadata_models.CustomMetadata` entries
into the typed :class:`~meca_engine.model.article.CustomMetaStore`
collections. Follows BR-071's deny-list-not-allow-list philosophy: every
entry ends up in exactly one output collection (never dropped) — most
commonly ``form_answers``, the catch-all for anything not matching a
more specific classification rule below.

**Classification signals, evidence-based** (verified against all 3 real
reference packages, not assumed): the ``<custom-meta>`` element's own
``specific-use`` attribute is the primary, authoritative signal —
``"form-files"`` (file entries), ``"question"`` (BR-075 reviewer
scorecard fields), ``"reviewer-decline"`` (BR-068 decline reasons).
``meta-name`` exact match handles ``"Decision Draft"`` (BR-069), which
carries no ``specific-use`` in the observed samples. Everything else
falls through to ``form_answers``, grouped by ``meta-name`` (multi-value
keys preserved, e.g. one real sample's ``"Authorship"`` key appears 4
times).

**Documented, non-inferred gap**: roughly two-thirds of one real
sample's entries carry no ``meta-name`` and no free ``meta-value`` text
at all — Kriyadocs' internal audit-trail markers (``specific-use`` values
``"history"``/``"lqc"``/``"query"``/``"summary"``, each carrying an actor/
role/timestamp but zero message text). These are **not** mapped into
``WorkflowLog``/``CorrespondenceEvent`` (which requires non-empty
``text``) — synthesizing text where none exists would violate this
milestone's explicit "do not infer missing events" instruction. They are
also not force-fit into ``form_answers`` (which requires a non-``None``
key in the vast majority of real, meaningful entries) — see the
Milestone 5B Architecture Compliance Report for the full evidence and
reasoning. The underlying raw data is never lost: Milestone 4's
``CustomMetadata.entries`` (this function's own input) remains the
complete, unmodified record regardless of what this classifier maps.

**Corrective-milestone fix (``specific-use="track-changes"`` exclusion)**:
a *different* audit-trail shape than the "no meta-name" one above — a
``track-changes`` entry **does** carry a real ``meta-name`` (e.g.
``"Figure 1"``, ``"PubData"``) and a non-empty value, so it previously
fell through to ``form_answers`` unfiltered. Confirmed against real
reference-package data: every one of these entries' value text is a
synthetic audit message of the literal form ``"<field> was changed"``
(nested under a ``<named-content specific-use="changeData">``), never
genuine business/form data — one real sample has 22 such entries, none
of which appear in that sample's own approved ``article.xml``. Excluded
the same way the "no meta-name" audit markers already are: not force-fit
into ``form_answers``, not synthesized into any other collection. See
`25_MILESTONE_6E_TRANSFORMATION_CORRECTIONS_REPORT.md` for the full
root cause and evidence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.model.article import (
    CustomMetaStore,
    DecisionDraft,
    DeclineReason,
    FileEntry,
    FormAnswerBag,
    FormAnswerEntry,
    ReviewerScorecard,
    WorkflowLog,
)
from meca_engine.model.enums import ReviewOutcomeStatus

if TYPE_CHECKING:
    from meca_engine.extraction.metadata_models import CustomMetadata, CustomMetaEntry
    from meca_engine.logging_.structured_logger import StructuredLogger

_STAGE = "extraction.custom_meta_classifier"

_SPECIFIC_USE_FILE_ENTRY = "form-files"
_SPECIFIC_USE_SCORECARD_FIELD = "question"
_SPECIFIC_USE_DECLINE_REASON = "reviewer-decline"
_SPECIFIC_USE_TRACK_CHANGES = "track-changes"
_DECISION_DRAFT_NAME = "Decision Draft"


def _attribute(entry: CustomMetaEntry, name: str) -> str | None:
    for attribute_name, value in entry.attributes:
        if attribute_name == name:
            return value
    return None


def _named_content(entry: CustomMetaEntry, content_type: str) -> str | None:
    for content_field in entry.named_content:
        if content_field.content_type == content_type:
            return content_field.text
    return None


def _specific_use(entry: CustomMetaEntry) -> str | None:
    return _attribute(entry, "specific-use")


def _build_file_entry(entry: CustomMetaEntry) -> FileEntry:
    declared_size_bytes = None
    size_text = _named_content(entry, "size")
    if size_text is not None and size_text.strip().isdigit():
        declared_size_bytes = int(size_text.strip())

    path_hint = _named_content(entry, "path") or ""
    round_label = path_hint.rsplit("/", 2)[-2] if path_hint.count("/") >= 2 else ""

    return FileEntry(
        round_label=round_label,
        category=_named_content(entry, "type") or "",
        original_filename=_named_content(entry, "name") or "",
        declared_path_hint=path_hint,
        declared_size_bytes=declared_size_bytes,
    )


def _build_decline_reason(entry: CustomMetaEntry) -> DeclineReason:
    round_label = (
        _attribute(entry, "data-article-version") or _attribute(entry, "data-version") or ""
    )
    reason_text = _named_content(entry, "decline-reason") or entry.value_text
    return DeclineReason(
        round_label=round_label,
        reviewer_name=_attribute(entry, "data-reviewer-name") or "",
        reason_text=reason_text,
    )


def _build_decision_draft(entry: CustomMetaEntry) -> DecisionDraft:
    return DecisionDraft(
        round_label=_attribute(entry, "data-version") or "",
        decision_text=entry.value_text,
    )


def classify(
    custom_metadata: CustomMetadata, *, logger: StructuredLogger | None = None
) -> CustomMetaStore:
    """Classify every extracted custom-metadata entry into the typed ICAM store.

    Args:
        custom_metadata: Milestone 4's unfiltered, flat extraction output.
        logger: Optional structured logger; logs a completion event
            carrying per-collection counts when given.

    Returns:
        The classified :class:`~meca_engine.model.article.CustomMetaStore`.
    """
    file_entries: list[FileEntry] = []
    decline_reasons: list[DeclineReason] = []
    decision_drafts: list[DecisionDraft] = []
    scorecard_answers: dict[tuple[str, str], list[tuple[str, str]]] = {}
    scorecard_identity: dict[tuple[str, str], tuple[str, str]] = {}
    form_answer_order: list[str] = []
    form_answer_values: dict[str, list[str]] = {}
    unclassified_no_name_count = 0
    unclassified_track_changes_count = 0

    for entry in custom_metadata.entries:
        specific_use = _specific_use(entry)

        if specific_use == _SPECIFIC_USE_FILE_ENTRY:
            file_entries.append(_build_file_entry(entry))
            continue

        if specific_use == _SPECIFIC_USE_DECLINE_REASON:
            decline_reasons.append(_build_decline_reason(entry))
            continue

        if specific_use == _SPECIFIC_USE_TRACK_CHANGES:
            unclassified_track_changes_count += 1
            continue

        if entry.name == _DECISION_DRAFT_NAME:
            decision_drafts.append(_build_decision_draft(entry))
            continue

        if specific_use == _SPECIFIC_USE_SCORECARD_FIELD and entry.name is not None:
            reviewer_email = _attribute(entry, "data-reviewer-email") or ""
            round_label = _attribute(entry, "data-version") or ""
            key = (reviewer_email, round_label)
            scorecard_answers.setdefault(key, []).append((entry.name, entry.value_text))
            scorecard_identity.setdefault(
                key, (_attribute(entry, "data-reviewer-name") or "", reviewer_email)
            )
            continue

        if entry.name is None:
            unclassified_no_name_count += 1
            continue

        if entry.name not in form_answer_values:
            form_answer_order.append(entry.name)
            form_answer_values[entry.name] = []
        form_answer_values[entry.name].append(entry.value_text)

    reviewer_scorecards = tuple(
        ReviewerScorecard(
            round_label=key[1],
            reviewer_name=scorecard_identity[key][0],
            reviewer_email=scorecard_identity[key][1],
            outcome_status=ReviewOutcomeStatus.COMPLETED,
            answers=tuple(answers),
        )
        for key, answers in scorecard_answers.items()
    )

    form_answers = FormAnswerBag(
        entries=tuple(
            FormAnswerEntry(key=name, values=tuple(form_answer_values[name]))
            for name in form_answer_order
        )
    )

    store = CustomMetaStore(
        form_answers=form_answers,
        file_entries=tuple(file_entries),
        reviewer_scorecards=reviewer_scorecards,
        decision_drafts=tuple(decision_drafts),
        decline_reasons=tuple(decline_reasons),
        workflow_log=WorkflowLog(),
    )

    if logger is not None:
        logger.info(
            "Custom-metadata classification complete",
            stage=_STAGE,
            context={
                "file_entry_count": len(store.file_entries),
                "reviewer_scorecard_count": len(store.reviewer_scorecards),
                "decision_draft_count": len(store.decision_drafts),
                "decline_reason_count": len(store.decline_reasons),
                "form_answer_count": len(store.form_answers.entries),
                "unclassified_no_name_count": unclassified_no_name_count,
                "unclassified_track_changes_count": unclassified_track_changes_count,
            },
        )
    return store
