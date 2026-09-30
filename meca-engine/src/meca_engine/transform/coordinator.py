"""Transformation Coordinator — Milestone 5B (11_LLD_02... §4.6).

The single place that knows the correct order to invoke every Milestone
5B transformation service and assemble the frozen ICAM via
:class:`~meca_engine.model.article.ArticleModelBuilder`. Propagates typed
errors from any stage unchanged (no re-wrapping — preserves the original
error class for correct retry/permanent classification downstream), per
the LLD's exact "Error Handling" description of this class.

Round resolution (`extraction.round_resolver`) and file resolution
(`extraction.file_resolver`) both need inputs this coordinator's own
caller must supply (the parsed document, for round resolution; the
staged root directory and media-type config, for file resolution) since
neither is derivable from the `ExtractionBundle` alone — see each
module's own docstring for why.

Custom-meta classification (`extraction.custom_meta_classifier`) now
runs *before* `_build_article_meta` (reordered in Milestone 5C): reviewer
and copy-editor contributor population needs the already-classified
`CustomMetaStore`, not the raw, unclassified `ExtractionBundle.custom`.

**Corrective-milestone fix (round-label reconciliation)**: `resolve_files`
already re-derives each file's authoritative round label from the
physical staged folder it was actually found under (`ResolvedFile.round_label`,
per BR-016 — the declared custom-meta `path` is "a hint only"). The
classified `CustomMetaStore.file_entries` this coordinator also freezes
into the ICAM previously kept `custom_meta_classifier`'s own,
independently-parsed `FileEntry.round_label` hint unchanged — which is
frequently wrong (e.g. a bare per-file staging-job uuid for any
`_temp/<uuid>/<file>`-style declared path, confirmed against real
reference-package data). This coordinator now overwrites each
`FileEntry.round_label` with its resolved counterpart *after* file
resolution completes, so every consumer of `custom_meta.file_entries`
(not just `resolved_files`) sees the one authoritative value. See
`25_MILESTONE_6E_TRANSFORMATION_CORRECTIONS_REPORT.md` for the full root
cause and evidence.
"""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import replace
from datetime import date
from typing import TYPE_CHECKING

from meca_engine.exceptions import ModelBuildError
from meca_engine.extraction.custom_meta_classifier import classify
from meca_engine.extraction.file_resolver import resolve_files
from meca_engine.extraction.navigation import as_int
from meca_engine.extraction.round_resolver import resolve_rounds
from meca_engine.logging_.performance import PerformanceTimer
from meca_engine.model.article import (
    Abstract,
    ArticleCounts,
    ArticleMeta,
    ArticleModelBuilder,
    HistoryDates,
)
from meca_engine.transform.body_fragment_builder import build_body_fragment
from meca_engine.transform.contributor_transformer import build_contributors_and_affiliations
from meca_engine.transform.identity_transformer import build_identity
from meca_engine.transform.journal_transformer import build_journal_meta
from meca_engine.transform.workflow_transformer import build_workflow_log

if TYPE_CHECKING:
    from meca_engine.config.schema import FeatureFlagsConfig, MediaTypeConfig
    from meca_engine.extraction.metadata_models import DateRecord, ExtractionBundle
    from meca_engine.extraction.parsed_model import ParsedDocument
    from meca_engine.logging_.structured_logger import StructuredLogger
    from meca_engine.model.article import ArticleModel, CustomMetaStore, FileEntry, ResolvedFile

_STAGE = "transform.coordinator"

# Corrective-milestone fix: the source `date-type` value for the
# "revision" history date varies by sample — confirmed directly against
# all 3 real reference packages: "rev-recd" (CS-2025-6808,
# CS-2025-8493_C) and "revision" (cs-2025-8827). Neither ever matches
# the literal "revised" this coordinator previously looked for alone,
# silently dropping this date on every real sample. "revised" is kept
# as a defensive synonym (the original, pre-fix behavior) though no
# sample demonstrates it.
_RECEIVED_DATE_TYPES = frozenset({"received"})
_REVISION_DATE_TYPES = frozenset({"revised", "rev-recd", "revision"})
_ACCEPTED_DATE_TYPES = frozenset({"accepted"})


class TransformationCoordinator:
    """Orchestrates every Milestone 5B transformation service into one frozen ICAM."""

    def __init__(
        self,
        *,
        media_type_config: MediaTypeConfig,
        logger: StructuredLogger | None = None,
        feature_flags: FeatureFlagsConfig | None = None,
    ) -> None:
        """Initialize the coordinator.

        Args:
            media_type_config: Extension-to-MIME-type mapping, forwarded
                to file resolution (ADR-008/009).
            logger: Optional structured logger; forwarded to every
                transformation service and to the
                :class:`~meca_engine.model.article.ArticleModelBuilder`
                it constructs.
            feature_flags: Milestone 10 (ADR-032) — only
                ``allow_filename_fallback`` is read, forwarded to
                :func:`~meca_engine.extraction.file_resolver.resolve_files`.
                ``None`` (every existing call site) is treated as the
                same lenient default `resolve_files` itself defaults to.
        """
        self._media_type_config = media_type_config
        self._logger = logger
        self._allow_filename_fallback = (
            feature_flags.allow_filename_fallback if feature_flags is not None else True
        )

    def build_model(
        self,
        *,
        article_id: str,
        source_object_key: str,
        staged_root: str,
        parsed_document: ParsedDocument,
        extraction_bundle: ExtractionBundle,
    ) -> ArticleModel:
        """Build and freeze the article's complete Internal Canonical Article Model.

        Args:
            article_id: The exact input-folder string (BR-003).
            source_object_key: The staged root XML's S3 key.
            staged_root: The root directory of this article's staged
                working folder (Milestone 2's staging output).
            parsed_document: Milestone 3's parsed document (for round
                resolution, which reads ``<article-version>`` directly).
            extraction_bundle: Milestone 4's complete extraction output.

        Returns:
            The frozen :class:`~meca_engine.model.article.ArticleModel`.

        Raises:
            RoundResolutionError: Propagated unchanged from
                :func:`~meca_engine.extraction.round_resolver.resolve_rounds`
                — only for a genuinely unresolvable round-ordering
                ambiguity (Milestone 11 recovers everything else).
            FileReferenceMissingError: Propagated unchanged from
                :func:`~meca_engine.extraction.file_resolver.resolve_files`
                — only when the ``manuscript``-category entry itself
                cannot be resolved (Milestone 11: every other category is
                skipped with a warning instead).
            ModelBuildError: Propagated unchanged from
                :meth:`~meca_engine.model.article.ArticleModelBuilder.freeze`.
        """
        if self._logger is not None:
            self._logger.info(
                "Transformation started", stage=_STAGE, context={"article_id": article_id}
            )

        builder = ArticleModelBuilder(article_id, logger=self._logger)
        timer = (
            PerformanceTimer(self._logger, _STAGE) if self._logger is not None else nullcontext()
        )

        with timer:
            custom_meta_store = classify(extraction_bundle.custom, logger=self._logger)
            custom_meta_store = replace(
                custom_meta_store, workflow_log=build_workflow_log(custom_meta_store)
            )

            resolved_files, file_warnings, skipped_indices = resolve_files(
                custom_meta_store.file_entries,
                staged_root,
                self._media_type_config,
                article_id=article_id,
                logger=self._logger,
                allow_filename_fallback=self._allow_filename_fallback,
            )
            custom_meta_store = replace(
                custom_meta_store,
                file_entries=_reconcile_file_entry_round_labels(
                    custom_meta_store.file_entries, resolved_files, skipped_indices
                ),
            )

            builder.set_identity(
                build_identity(
                    extraction_bundle.article,
                    extraction_bundle.journal,
                    article_id=article_id,
                    source_object_key=source_object_key,
                )
            )
            builder.set_journal_meta(build_journal_meta(extraction_bundle.journal))
            builder.set_article_meta(
                self._build_article_meta(extraction_bundle, custom_meta_store, logger=self._logger)
            )
            builder.set_body_fragment(build_body_fragment(parsed_document))
            builder.set_custom_meta(custom_meta_store)

            rounds, round_warnings = resolve_rounds(parsed_document, article_id=article_id)
            builder.set_rounds(rounds)
            builder.set_resolved_files(resolved_files)
            all_warnings = file_warnings + round_warnings
            if all_warnings:
                builder.set_warnings(all_warnings)

        model = builder.freeze()

        if self._logger is not None:
            self._logger.info(
                "Transformation completed", stage=_STAGE, context={"article_id": article_id}
            )
        return model

    def _build_article_meta(
        self,
        extraction_bundle: ExtractionBundle,
        custom_meta_store: CustomMetaStore,
        *,
        logger: StructuredLogger | None,
    ) -> ArticleMeta:
        article = extraction_bundle.article
        contributors, affiliations, corresponding_emails = build_contributors_and_affiliations(
            extraction_bundle.contributors,
            reviewer_scorecards=custom_meta_store.reviewer_scorecards,
            decline_reasons=custom_meta_store.decline_reasons,
            form_answers=custom_meta_store.form_answers,
            logger=logger,
        )
        return ArticleMeta(
            display_channel_subject=article.display_channel_subject or "",
            article_title=article.title or "",
            abstracts=tuple(
                Abstract(text=a.text, abstract_type=a.abstract_type, language=a.language)
                for a in article.abstracts
            ),
            contributors=contributors,
            affiliations=affiliations,
            corresponding_emails=corresponding_emails,
            heading_subjects=article.heading_subjects,
            copyright_statement=article.copyright_statement,
            copyright_year=article.copyright_year,
            funding=article.funding_statements,
            keywords=article.keywords,
            counts=ArticleCounts(
                word_count=as_int(article.word_count),
                ref_count=as_int(article.ref_count),
                fig_count=as_int(article.fig_count),
                table_count=as_int(article.table_count),
                equation_count=as_int(article.equation_count),
                page_count=as_int(article.page_count),
            ),
            history_dates=HistoryDates(
                received=_find_date(article.history_dates, _RECEIVED_DATE_TYPES),
                revision=_find_date(article.history_dates, _REVISION_DATE_TYPES),
                accepted=_find_date(article.history_dates, _ACCEPTED_DATE_TYPES),
            ),
            pub_dates=tuple(
                (record.date_type, converted)
                for record in article.pub_dates
                if record.date_type is not None and (converted := _to_date(record)) is not None
            ),
        )


def _find_date(records: tuple[DateRecord, ...], date_types: frozenset[str]) -> date | None:
    for record in records:
        if record.date_type in date_types:
            return _to_date(record)
    return None


def _to_date(record: DateRecord) -> date | None:
    year = as_int(record.year)
    if year is None:
        return None
    month = as_int(record.month) or 1
    day = as_int(record.day) or 1
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _reconcile_file_entry_round_labels(
    file_entries: tuple[FileEntry, ...],
    resolved_files: tuple[ResolvedFile, ...],
    skipped_indices: tuple[int, ...],
) -> tuple[FileEntry, ...]:
    """Overwrite each resolved `FileEntry.round_label` with its physical counterpart.

    `resolve_files` returns one :class:`~meca_engine.model.article.ResolvedFile`
    per *successfully resolved* input `FileEntry`, in the same relative
    order, plus the positions of any entries it skipped (Milestone 11 —
    see its own docstring for why a skipped entry has no physical
    location to reconcile from). `round_label` on a `ResolvedFile` is the
    staged folder the file was *actually found under* (BR-016), never
    the declared-path hint this module's `FileEntry.round_label` started
    as. Reconciling here means every consumer of `custom_meta.file_entries`
    (not only `resolved_files`) sees the one authoritative value for
    every entry that has one; a skipped entry keeps its original,
    hint-only `round_label` unchanged — it was never physically located,
    so there is nothing authoritative to overwrite it with.
    """
    skipped = set(skipped_indices)
    expected_resolved_count = len(file_entries) - len(skipped)
    if expected_resolved_count != len(resolved_files):
        raise ModelBuildError(
            f"resolve_files returned {len(resolved_files)} resolved entries and "
            f"{len(skipped)} skipped indices for {len(file_entries)} input "
            f"file_entries — its documented contract was violated"
        )
    resolved_iter = iter(resolved_files)
    return tuple(
        entry if index in skipped else replace(entry, round_label=next(resolved_iter).round_label)
        for index, entry in enumerate(file_entries)
    )
