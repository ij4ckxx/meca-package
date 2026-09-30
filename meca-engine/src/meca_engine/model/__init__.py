"""Internal Canonical Article Model (ICAM) — the one object every generator consumes.

Per 11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §3-4. Implemented in Milestone
5A: the domain model, builder, serialization, and structural validation.
**Not implemented yet**: any extraction-stage class that actually
populates an `ArticleModelBuilder` from real source data (`KriyadocsParser`,
`CustomMetaClassifier`, `RoundResolver`, `FileResolver`,
`TransformationCoordinator` — all Milestone 5B) — see `model.builders`
for interface-only previews of that future work.
"""

from __future__ import annotations

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
from meca_engine.model.builders import (
    ArticleBuilder,
    AssetBuilder,
    ContributorBuilder,
    JournalBuilder,
    WorkflowBuilder,
)
from meca_engine.model.enums import (
    ActorRole,
    ContribType,
    CorrespondenceChannel,
    CorrespondenceKind,
    ReviewOutcomeStatus,
)
from meca_engine.model.serialization import SCHEMA_VERSION, from_dict, to_dict
from meca_engine.model.validation import (
    StructuralIssue,
    StructuralIssueSeverity,
    validate_structural_integrity,
)

__all__ = [
    "SCHEMA_VERSION",
    "Abstract",
    "ActorRole",
    "Affiliation",
    "ArticleBuilder",
    "ArticleCounts",
    "ArticleIdentity",
    "ArticleMeta",
    "ArticleModel",
    "ArticleModelBuilder",
    "AssetBuilder",
    "BodyFragment",
    "ContribType",
    "Contributor",
    "ContributorBuilder",
    "CorrespEmail",
    "CorrespondenceChannel",
    "CorrespondenceEvent",
    "CorrespondenceKind",
    "CustomMetaStore",
    "DecisionDraft",
    "DeclineReason",
    "FileEntry",
    "FormAnswerBag",
    "FormAnswerEntry",
    "HistoryDates",
    "JournalBuilder",
    "JournalMeta",
    "ResolvedFile",
    "ReviewOutcomeStatus",
    "ReviewerScorecard",
    "RoundInfo",
    "StructuralIssue",
    "StructuralIssueSeverity",
    "WorkflowBuilder",
    "WorkflowLog",
    "from_dict",
    "to_dict",
    "validate_structural_integrity",
]
