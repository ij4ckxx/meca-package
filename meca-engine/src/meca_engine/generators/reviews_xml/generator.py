"""Reviews XML Generator — produces <ArticleID>_reviews.xml (Business Rule Book §G, BR-096–125).

Implemented in Milestone 6F, reusing the Generator Framework (Milestone
6A) exactly as raw.xml/article.xml/manifest.xml do. Per
11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.7: "the most complex
generator — delegates to `review_builder` and `decision_builder`;
applies ADR-004/005 feature-flag scoping." Depends on **no other
generator** — only the ICAM (`model.custom_meta`, `model.rounds`,
`model.identity`, and — since BR-163 — `model.article_meta.contributors`,
read-only, for the already-correlated reviewer-identity lookup) and
configuration (`ReviewsXmlConfig`, `FeatureFlagsConfig`,
`NamespaceManager`), matching manifest.xml's "no generator-to-generator
dependency" precedent (Milestone 6D) — this reads the same ICAM object
every generator already receives, not a new dependency on
`article_xml`'s own generator.

**This is, by a wide margin, the least mechanically-derivable of the 4
generators built so far** — see `26_REVIEWS_DECISION_LOG.md` for the
full evidence trail. In summary: direct inspection of all 3 real
reference packages' own `reviews.xml` shows their richest content
(per-reviewer recommendation text, author/confidential comment splits,
multi-point screening-checklist items, editor identity, every date) was
manually curated by a human reading raw correspondence logs — content
that has **no corresponding structured ICAM field today**
(`ReviewerScorecard.overall_recommendation`/`.assigned_date`/`.due_date`/
`.submitted_date`, `DecisionDraft.editor_name`/`.associate_editor_name`/
`.decision_date`, and `WorkflowLog.events` are confirmed always
`None`/empty on all 3 real samples). Per this milestone's explicit
"never fabricate missing history" / "if information is incomplete: emit
diagnostics... never synthesize workflow history" instructions, this
generator renders only what the ICAM actually carries and diagnoses
every gap — it does not attempt to parse recommendation/editor/date
facts out of free text, which would require inventing unapproved
extraction logic.

**Evidence-based BR implementation status** (see the Business Rule
Traceability table in `27_MILESTONE_6F_REVIEWS_XML_GENERATOR_REPORT.md`
for full detail): BR-096/097/099/100/101/102/106/107/109/112/120/121/122
are fully implemented and evidence-backed. BR-103/104/105/108/110/111/
114/115/116/117/118/119 are structurally supported where the
corresponding ICAM field exists (dates, extended history, duplicate
correspondence) but never populated by any of the 3 real samples today
— diagnosed as unavailable rather than fabricated. BR-098's canonical
4-attribute schema is applied to every `review-type="review"` block
(2/3-confirmed canonical target; CS-2025-6808's own reference package
omits it — a confirmed, documented, non-replicated defect, per BR-098's
own text).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.exceptions import GeneratorInvariantError
from meca_engine.generators.base import BaseGenerator
from meca_engine.generators.reviews_xml.decision_builder import build_decision_reviews
from meca_engine.generators.reviews_xml.document import ReviewsXmlDocument
from meca_engine.generators.reviews_xml.review_builder import (
    build_decline_reviews,
    build_extended_history_reviews,
    build_scorecard_reviews,
    build_structured_reviewer_lookup,
)
from meca_engine.generators.xml.builder import DoctypeDeclaration, XmlDocumentBuilder

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from meca_engine.config.schema import ReviewsXmlConfig
    from meca_engine.generators.context import GeneratorContext
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.xml.namespaces import NamespaceManager
    from meca_engine.model.collections import RoundIndex

_GENERATOR_NAME = "reviews_xml"
_REVIEWS_NAMESPACE_PREFIX = "meca-reviews"
_XLINK_NAMESPACE_PREFIX = "xlink"
_ALI_NAMESPACE_PREFIX = "ali"
_REVIEW_BLOCK_ORDER = 0
_DECISION_BLOCK_ORDER = 1
_UNRESOLVED_ROUND_SORT_KEY = 2**31


class ReviewsXmlGenerator(BaseGenerator[ReviewsXmlDocument]):
    """Generates reviews.xml from the ICAM. See module docstring for BR traceability."""

    def __init__(
        self,
        *,
        namespace_manager: NamespaceManager,
        reviews_xml_config: ReviewsXmlConfig,
    ) -> None:
        """Initialize the generator.

        Args:
            namespace_manager: Resolves BR-096's default/`xlink`/`ali` namespaces.
            reviews_xml_config: BR-096/097/100/101/120/122's externalized constants.
        """
        self._namespace_manager = namespace_manager
        self._config = reviews_xml_config

    @property
    def generator_name(self) -> str:
        """This generator's stable name, ``"reviews_xml"``."""
        return _GENERATOR_NAME

    def _generate(self, context: GeneratorContext) -> ReviewsXmlDocument:
        model = context.model
        config = self._config
        diagnostics = context.diagnostics
        custom_meta = model.custom_meta

        builder = XmlDocumentBuilder()
        root = builder.create_root(
            "review-group",
            attributes={
                "xmlns": self._require_uri(_REVIEWS_NAMESPACE_PREFIX),
                "xmlns:xlink": self._require_uri(_XLINK_NAMESPACE_PREFIX),
                "xmlns:ali": self._require_uri(_ALI_NAMESPACE_PREFIX),
                "content-version": config.content_version,  # BR-097
            },
        )

        # BR-163: reuse the already-correlated reviewer identities built for
        # article.xml's own contrib-group (see `build_structured_reviewer_lookup`)
        # — reads the same ICAM `context.model` every generator already has,
        # not a new generator-to-generator dependency.
        structured_lookup = build_structured_reviewer_lookup(model.article_meta.contributors)
        review_blocks = (
            *build_scorecard_reviews(
                builder, config, custom_meta.reviewer_scorecards, diagnostics, structured_lookup
            ),
            *build_decline_reviews(
                builder, config, custom_meta.decline_reasons, diagnostics, structured_lookup
            ),
            *build_extended_history_reviews(
                builder, config, context.feature_flags, custom_meta.workflow_log, diagnostics
            ),
        )
        decision_blocks = build_decision_reviews(
            builder, config, custom_meta.decision_drafts, diagnostics
        )

        if not review_blocks and not decision_blocks:
            diagnostics.info(_GENERATOR_NAME, "No review or decision history available")

        for review in _order_blocks(review_blocks, decision_blocks, model.rounds, diagnostics):
            root.append(review)

        xml_bytes = builder.serialize(
            root,
            pretty=True,
            encoding=config.encoding,  # BR-120
            indent_spaces=config.pretty_indent_spaces,
            doctype=DoctypeDeclaration(  # BR-096
                root_tag="review-group",
                public_id=config.doctype_public_id,
                system_id=config.doctype_system_id,
            ),
        )

        return ReviewsXmlDocument(
            article_id=model.identity.article_id,
            filename=config.reviews_filename_pattern.format(  # BR-122
                article_id=model.identity.article_id
            ),
            xml_bytes=xml_bytes,
        )

    def _require_uri(self, prefix: str) -> str:
        uri = self._namespace_manager.uri_for(prefix)
        if uri is None:
            raise GeneratorInvariantError(
                f"Namespace prefix {prefix!r} is not registered in the namespace configuration",
                stage=_GENERATOR_NAME,
            )
        return uri


def _order_blocks(
    review_blocks: tuple[Element, ...],
    decision_blocks: tuple[Element, ...],
    rounds: RoundIndex,
    diagnostics: DiagnosticsCollector,
) -> list[Element]:
    """BR-123: chronological, grouped by round (earliest round first, reviews before decisions).

    Round resolution is by exact ``review-version`` ↔ ``RoundInfo.label``
    string match only — per this milestone's explicit "do not introduce
    additional round inference" instruction, no heuristic beyond the
    already-approved `RoundIndex` (Milestone 6E) is used. A
    ``review-version`` with no matching `RoundInfo` is diagnosed and
    sorted after every resolved round, never dropped.
    """
    round_sequence_by_label = {
        round_info.label: round_info.sequence_number for round_info in rounds
    }
    tagged = [(_REVIEW_BLOCK_ORDER, element) for element in review_blocks] + [
        (_DECISION_BLOCK_ORDER, element) for element in decision_blocks
    ]

    unresolved_labels: set[str] = set()
    keyed: list[tuple[tuple[int, int], Element]] = []
    for block_order, element in tagged:
        round_label = element.get("review-version") or ""
        sequence_number = round_sequence_by_label.get(round_label)
        if sequence_number is None:
            unresolved_labels.add(round_label)
            keyed.append(((_UNRESOLVED_ROUND_SORT_KEY, block_order), element))
        else:
            keyed.append(((sequence_number, block_order), element))

    for label in sorted(unresolved_labels):
        diagnostics.warn(
            _GENERATOR_NAME,
            f"review-version {label!r} does not match any round in the round "
            f"index; sorted after every resolved round (BR-123)",
        )
    return [element for _, element in sorted(keyed, key=lambda pair: pair[0])]
