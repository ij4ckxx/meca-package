"""Metadata → ICAM Transformation Layer — Milestone 5B.

Consumes Milestone 3's `ParsedDocument` and Milestone 4's `ExtractionBundle`
and produces a fully populated, frozen `model.ArticleModel`. Contains
**no metadata mapping beyond identifying/copying already-extracted
values, no DOI generation, no business-rule transformation that modifies
values, no XML generation, no validation engine** — see each module's own
docstring for its exact, individually-justified scope.

`TransformationCoordinator` (`coordinator.py`) is the single orchestrating
entry point; every other module here is an independent, single-
responsibility transformation service it invokes in order.
"""

from __future__ import annotations

from meca_engine.transform.body_fragment_builder import build_body_fragment
from meca_engine.transform.contributor_transformer import build_contributors_and_affiliations
from meca_engine.transform.coordinator import TransformationCoordinator
from meca_engine.transform.identity_transformer import build_identity
from meca_engine.transform.journal_transformer import build_journal_meta
from meca_engine.transform.workflow_transformer import build_workflow_log

__all__ = [
    "TransformationCoordinator",
    "build_body_fragment",
    "build_contributors_and_affiliations",
    "build_identity",
    "build_journal_meta",
    "build_workflow_log",
]
