"""Workflow transformation — Milestone 5B.

Builds the ICAM's `WorkflowLog` from custom-meta-classified correspondence
data (`meca_engine.extraction.custom_meta_classifier`'s output already
carries a `WorkflowLog` on its `CustomMetaStore` result — see that
module's docstring for why it is currently always empty against the 3
real reference packages: Kriyadocs' custom-meta correspondence-shaped
entries carry an actor/role/timestamp but no free-text message, and this
project's explicit "do not infer missing events" instruction forbids
synthesizing text where none exists).

This module exists as the documented seam for Milestone 6+ to extend once
a real free-text-bearing correspondence source is confirmed — today it is
a thin, honest pass-through, not a placeholder pretending to do more than
it does. `RoundInfo`/`RoundIndex` are **not** built here — see
`meca_engine.extraction.round_resolver`, which reads `<article-version>`
directly (BR-010); "workflow metadata" (Milestone 4's generic `<event>`/
`<stage>`-based `WorkflowMetadata`) and "round metadata" are genuinely
different source concepts in the real reference packages, confirmed by
inspection: Milestone 4's `WorkflowMetadata.events` capture Kriyadocs'
internal production-pipeline telemetry (job stages, timestamps, word
counts) — operationally interesting, but not part of the ICAM's object
graph (11_LLD_02... §3.2 has no slot for it) and therefore not mapped by
this or any Milestone 5B transformer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meca_engine.model.article import CustomMetaStore, WorkflowLog


def build_workflow_log(custom_meta_store: CustomMetaStore) -> WorkflowLog:
    """Return the article's workflow log.

    Args:
        custom_meta_store: The already-classified
            :class:`~meca_engine.model.article.CustomMetaStore` (built by
            :func:`meca_engine.extraction.custom_meta_classifier.classify`).

    Returns:
        The store's own :attr:`~meca_engine.model.article.CustomMetaStore.workflow_log`,
        unchanged — see module docstring for why no further correspondence
        events are synthesized here.
    """
    return custom_meta_store.workflow_log
