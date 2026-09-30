"""Engine warnings — Milestone 10 (Generate-With-Warnings policy, ADR-032).

A warning is a structured, queryable record of a specification deviation
the engine recovered from *without* aborting generation — as opposed to
an exception (`meca_engine.exceptions`), which stops generation entirely.
Warnings are first-class ICAM data, not a logging side-channel: they
travel on :class:`~meca_engine.model.article.ArticleModel` itself, so
every consumer that already holds the model (`PackageBuilder`, the batch
runner, a future dashboard, JSON export via
``dataclasses.asdict``/``json.dumps``) can read them without re-running
any validation.

**Deliberately not the same type as** `extraction.parsed_model.ParseDiagnostic`
or `generators.diagnostics.GeneratorDiagnostic` — both of those are
scoped to their own layer and already dead-end after it (parse-time
observations never survive past `ExtractionBundle`; generator-time
observations never survive past one `GenerationResult`). `EngineWarning`
is the first diagnostic type designed to survive all the way to a
built package. Per this project's established layering rule (`model`
is never allowed to import `extraction` or `generators`), this module
defines its own severity enum rather than importing either of the other
two — the same reasoning `generators/diagnostics.py` already documents
for not importing `extraction`'s version.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


@unique
class WarningSeverity(str, Enum):
    """How serious an :class:`EngineWarning` is. Model-local — see module docstring."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@unique
class WarningCategory(str, Enum):
    """What kind of specification deviation an :class:`EngineWarning` records."""

    MISSING_REQUIRED_METADATA = "missing_required_metadata"
    SPECIFICATION_FALLBACK = "specification_fallback"
    SOURCE_DATA_INCONSISTENCY = "source_data_inconsistency"
    BUSINESS_RULE_WARNING = "business_rule_warning"


@unique
class FindingOrigin(str, Enum):
    """Whose responsibility a finding is — orthogonal to :class:`WarningCategory`.

    Milestone 11 (archive-migration philosophy shift): separates *what
    kind of deviation* a finding records (:class:`WarningCategory`, the
    existing axis) from *who is responsible for it* — the engine itself,
    the submitted source data, a business-rule interpretation, engine
    configuration, or nothing actionable at all. Conversion reports
    group and prioritize findings along this axis.
    """

    ENGINE_DEFECT = "engine_defect"
    SOURCE_DATA_ISSUE = "source_data_issue"
    BUSINESS_RULE_VIOLATION = "business_rule_violation"
    CONFIGURATION_ISSUE = "configuration_issue"
    INFORMATIONAL = "informational"


@unique
class ConfidenceLevel(str, Enum):
    """How confident the engine is in a finding or recovery (Milestone 12).

    Reporting-only — never used to alter engine behavior. A deterministic
    recovery (e.g. deriving a filename from its own declared path) is
    ``HIGH``; an omission made because a value is simply unavailable is
    ``MEDIUM``; a heuristic/tolerant match (e.g. matching a file by
    normalized-whitespace similarity) is ``LOW``.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class EngineWarning:
    """One recorded specification deviation the engine recovered from.

    Attributes:
        code: A stable, machine-matchable identifier (e.g.
            ``"BR013_FALLBACK_FILENAME_FROM_PATH"``).
        category: Which structured category this warning belongs to.
        severity: How serious this warning is.
        origin: Whose responsibility this finding is (Milestone 11) —
            see :class:`FindingOrigin`.
        rule_id: The **Business Rule** Book identifier this relates to
            (e.g. ``"BR-013"``) — the rule that could not be fully
            satisfied. Deliberately separate from ``recovery_rule_id``
            (Milestone 12: Business Rules and Recovery Rules are two
            distinct catalogs — see `model/recovery_rules.py`). ``None``
            when no single Business Rule applies.
        recovery_rule_id: The **Recovery Rule** Book identifier (e.g.
            ``"RR-002"``, see `model/recovery_rules.py`) describing how
            the engine proceeded, when ``is_recovery`` is ``True``.
            ``None`` for a purely advisory finding that involved no
            recovery.
        confidence: How confident the engine is in this finding/recovery
            (Milestone 12) — reporting-only, see :class:`ConfidenceLevel`.
        message: A human-readable description of what happened.
        article_id: The article this warning pertains to.
        suggested_action: What a human reviewer should consider doing
            about this, if anything.
        is_recovery: ``True`` when the engine actually altered, omitted,
            or derived something to make generation possible (Milestone
            11's Recovery + Warning framework); ``False`` for a purely
            advisory/informational finding that required no engine
            action. Never set silently — every ``True`` instance must be
            paired with a code/message describing exactly what was
            recovered. Conversion reports and package-status computation
            both key off this flag to distinguish "generated cleanly but
            worth reviewing" from "generated only because the engine
            compensated for something."
        affected_file: The specific declared or physical filename this
            finding concerns, when it is file-specific. ``None`` for a
            round-level or package-level finding.
        context: Open-ended structured detail specific to this warning's
            `code` (e.g. the round/category/derived filename/declared
            path for a filename-fallback warning), as ordered key-value
            pairs — mirrors `generators.diagnostics.GeneratorDiagnostic
            .context`'s open-vocabulary design, but a tuple of pairs
            rather than a ``dict``: ``ArticleModel`` (which carries
            these) must stay hashable per its own tested contract, and a
            ``dict``-valued field would silently break that whenever a
            warning existed. Use :meth:`context_dict` for ``dict``-style
            access.
    """

    code: str
    category: WarningCategory
    severity: WarningSeverity
    origin: FindingOrigin
    rule_id: str | None
    recovery_rule_id: str | None
    confidence: ConfidenceLevel
    message: str
    article_id: str | None
    suggested_action: str | None
    is_recovery: bool = False
    affected_file: str | None = None
    context: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def context_dict(self) -> Mapping[str, str]:
        """A ``dict``-style view of :attr:`context`, for convenient lookup."""
        return dict(self.context)
