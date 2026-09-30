"""Checkpoint data model: pipeline stages and per-article checkpoint records.

Per 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.12 and
13_LLD_04_PIPELINE_SCALABILITY_VALIDATION.md §9.5: checkpointing is
per-article, per-stage, using the stage names enumerated in
06_DATA_FLOW_DOCUMENT.md. Milestone 2 (Input & Staging Layer) only ever
produces ``NOT_STARTED``, ``STAGING``, ``STAGED``, and ``FAILED`` records —
every later stage is defined here now (rather than added piecemeal in
later milestones) purely because it is an enum of names, not business
logic, and defining the complete state machine once avoids a breaking
change to the :class:`~meca_engine.checkpoint.store.CheckpointStore`
contract later.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@unique
class ArticleStage(str, Enum):
    """A single article's position in the end-to-end processing pipeline.

    Values (other than ``STAGED``) match 06_DATA_FLOW_DOCUMENT.md's own
    checkpoint stage names exactly, so a checkpoint record's ``stage``
    field is directly cross-referenceable against that document.

    ``STAGED`` is a Milestone 2 addition: the Data Flow Document's
    granularity jumps directly from ``staging`` to ``metadata-loaded``,
    but Milestone 2 must be able to represent "staging finished
    successfully" without implying metadata loading (XML parsing) has
    happened, since that remains out of scope until Milestone 3. This is
    an additive refinement of the existing per-stage granularity
    (13_LLD_04... §9.5), not a new checkpointing concept.
    """

    NOT_STARTED = "not_started"
    STAGING = "staging"
    STAGED = "staged"
    METADATA_LOADED = "metadata-loaded"
    PRE_VALIDATED = "pre-validated"
    TRANSFORMED = "transformed"
    GENERATED = "generated"
    CROSS_REFERENCED = "cross-referenced"
    VALIDATED = "validated"
    PACKAGED = "packaged"
    PUBLISHED_OPERATIONAL = "published-operational"
    ARCHIVED = "archived"
    FAILED = "failed"


# The linear progression order for every non-terminal-failure stage. FAILED
# is deliberately excluded — it is a terminal state reachable from any
# in-progress stage, not a position within the linear order.
STAGE_ORDER: tuple[ArticleStage, ...] = (
    ArticleStage.NOT_STARTED,
    ArticleStage.STAGING,
    ArticleStage.STAGED,
    ArticleStage.METADATA_LOADED,
    ArticleStage.PRE_VALIDATED,
    ArticleStage.TRANSFORMED,
    ArticleStage.GENERATED,
    ArticleStage.CROSS_REFERENCED,
    ArticleStage.VALIDATED,
    ArticleStage.PACKAGED,
    ArticleStage.PUBLISHED_OPERATIONAL,
    ArticleStage.ARCHIVED,
)


def stage_index(stage: ArticleStage) -> int:
    """Return a stage's position in the linear pipeline order.

    Args:
        stage: The stage to look up. Must not be ``ArticleStage.FAILED``
            (failure is a terminal branch, not a position in the order).

    Returns:
        The zero-based index of ``stage`` within :data:`STAGE_ORDER`.

    Raises:
        ValueError: If ``stage`` is ``ArticleStage.FAILED`` or otherwise
            not present in :data:`STAGE_ORDER`.
    """
    return STAGE_ORDER.index(stage)


@dataclass(frozen=True)
class CheckpointRecord:
    """An immutable snapshot of one article's checkpoint state.

    Attributes:
        article_id: The article this record describes.
        stage: The article's current pipeline stage.
        updated_at: When this record was last written.
        failure_reason: A short, human-readable failure description, set
            only when ``stage`` is ``ArticleStage.FAILED``.
    """

    article_id: str
    stage: ArticleStage
    updated_at: datetime
    failure_reason: str | None = None
