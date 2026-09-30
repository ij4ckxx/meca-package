"""Metadata Extraction Layer orchestration — Milestone 4.

The single entry point that runs all seven independent extractors over
one :class:`~meca_engine.extraction.parsed_model.ParsedDocument` and
combines their results into one
:class:`~meca_engine.extraction.metadata_models.ExtractionBundle`.

Logging is deliberately concentrated here, not inside any individual
extractor: each extractor stays a pure function (maximally testable in
isolation), while this orchestrator logs start/completion and diagnostic
counts per extractor and times each one with
:class:`~meca_engine.logging_.performance.PerformanceTimer`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.extraction.article_metadata_extractor import extract_article_metadata
from meca_engine.extraction.asset_metadata_extractor import extract_asset_metadata
from meca_engine.extraction.contributor_metadata_extractor import extract_contributor_metadata
from meca_engine.extraction.cross_reference_extractor import extract_cross_references
from meca_engine.extraction.custom_metadata_extractor import extract_custom_metadata
from meca_engine.extraction.journal_metadata_extractor import extract_journal_metadata
from meca_engine.extraction.metadata_models import ExtractionBundle
from meca_engine.extraction.workflow_metadata_extractor import extract_workflow_metadata
from meca_engine.logging_.performance import PerformanceTimer

if TYPE_CHECKING:
    from meca_engine.extraction.parsed_model import ParsedDocument, ParseDiagnostic
    from meca_engine.logging_.structured_logger import StructuredLogger

_STAGE_PREFIX = "extraction.metadata"


def extract_all_metadata(document: ParsedDocument, logger: StructuredLogger) -> ExtractionBundle:
    """Run every metadata extractor over one parsed document.

    Args:
        document: The parsed document to extract from.
        logger: Logs one start event, one completion event (carrying the
            diagnostic count), and one :class:`PerformanceTimer` reading
            per extractor.

    Returns:
        The combined :class:`~meca_engine.extraction.metadata_models.ExtractionBundle`,
        with every extractor's diagnostics flattened into one tuple, in
        extractor-then-document order.
    """
    diagnostics: list[ParseDiagnostic] = []

    logger.info("Starting article metadata extraction", stage=f"{_STAGE_PREFIX}.article")
    with PerformanceTimer(logger, f"{_STAGE_PREFIX}.article"):
        article, article_diagnostics = extract_article_metadata(document)
    diagnostics.extend(article_diagnostics)
    logger.info(
        "Completed article metadata extraction",
        stage=f"{_STAGE_PREFIX}.article",
        context={"diagnostic_count": len(article_diagnostics)},
    )

    logger.info("Starting contributor metadata extraction", stage=f"{_STAGE_PREFIX}.contributor")
    with PerformanceTimer(logger, f"{_STAGE_PREFIX}.contributor"):
        contributors, contributor_diagnostics = extract_contributor_metadata(document)
    diagnostics.extend(contributor_diagnostics)
    logger.info(
        "Completed contributor metadata extraction",
        stage=f"{_STAGE_PREFIX}.contributor",
        context={"diagnostic_count": len(contributor_diagnostics)},
    )

    logger.info("Starting journal metadata extraction", stage=f"{_STAGE_PREFIX}.journal")
    with PerformanceTimer(logger, f"{_STAGE_PREFIX}.journal"):
        journal, journal_diagnostics = extract_journal_metadata(document)
    diagnostics.extend(journal_diagnostics)
    logger.info(
        "Completed journal metadata extraction",
        stage=f"{_STAGE_PREFIX}.journal",
        context={"diagnostic_count": len(journal_diagnostics)},
    )

    logger.info("Starting workflow metadata extraction", stage=f"{_STAGE_PREFIX}.workflow")
    with PerformanceTimer(logger, f"{_STAGE_PREFIX}.workflow"):
        workflow, workflow_diagnostics = extract_workflow_metadata(document)
    diagnostics.extend(workflow_diagnostics)
    logger.info(
        "Completed workflow metadata extraction",
        stage=f"{_STAGE_PREFIX}.workflow",
        context={"diagnostic_count": len(workflow_diagnostics)},
    )

    logger.info("Starting custom metadata extraction", stage=f"{_STAGE_PREFIX}.custom")
    with PerformanceTimer(logger, f"{_STAGE_PREFIX}.custom"):
        custom, custom_diagnostics = extract_custom_metadata(document)
    diagnostics.extend(custom_diagnostics)
    logger.info(
        "Completed custom metadata extraction",
        stage=f"{_STAGE_PREFIX}.custom",
        context={"diagnostic_count": len(custom_diagnostics)},
    )

    logger.info("Starting asset metadata extraction", stage=f"{_STAGE_PREFIX}.asset")
    with PerformanceTimer(logger, f"{_STAGE_PREFIX}.asset"):
        assets, asset_diagnostics = extract_asset_metadata(document)
    diagnostics.extend(asset_diagnostics)
    logger.info(
        "Completed asset metadata extraction",
        stage=f"{_STAGE_PREFIX}.asset",
        context={"diagnostic_count": len(asset_diagnostics)},
    )

    logger.info("Starting cross-reference extraction", stage=f"{_STAGE_PREFIX}.cross_reference")
    with PerformanceTimer(logger, f"{_STAGE_PREFIX}.cross_reference"):
        cross_references, cross_reference_diagnostics = extract_cross_references(document)
    diagnostics.extend(cross_reference_diagnostics)
    logger.info(
        "Completed cross-reference extraction",
        stage=f"{_STAGE_PREFIX}.cross_reference",
        context={"diagnostic_count": len(cross_reference_diagnostics)},
    )

    return ExtractionBundle(
        article=article,
        contributors=contributors,
        journal=journal,
        workflow=workflow,
        custom=custom,
        assets=assets,
        cross_references=cross_references,
        diagnostics=tuple(diagnostics),
    )
