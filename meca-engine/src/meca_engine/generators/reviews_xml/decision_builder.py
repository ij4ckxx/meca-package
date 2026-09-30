"""Decision-block construction — one ``<review review-type="decision">`` per round.

BR-109/110/113. See ``generator.py``'s module docstring for the full
BR/ADR traceability and `26_REVIEWS_DECISION_LOG.md` for the judgment
call this module makes: BR-110's generated summary sentence
("Send for major revisions. Decision letter issued <date> by Editor
<name>...") is never synthesized — ``DecisionDraft.editor_name``,
``.associate_editor_name``, and ``.decision_date`` are always ``None``
on all 3 real reference packages, and the outcome/editor identity only
exists as unstructured text *inside* ``decision_text`` itself, which
this generator does not parse (that would require inventing free-text
extraction logic never evidenced or approved).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.generators.reviews_xml.review_builder import add_review_item, add_reviews_contrib

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from meca_engine.config.schema import ReviewsXmlConfig
    from meca_engine.generators.diagnostics import DiagnosticsCollector
    from meca_engine.generators.xml.builder import XmlDocumentBuilder
    from meca_engine.model.article import DecisionDraft

_GENERATOR_NAME = "reviews_xml"
_DECISION_TYPE = "decision"


def build_decision_reviews(
    builder: XmlDocumentBuilder,
    config: ReviewsXmlConfig,
    decision_drafts: tuple[DecisionDraft, ...],
    diagnostics: DiagnosticsCollector,
) -> tuple[Element, ...]:
    """BR-109: one review-type="decision" block per round's editorial decision."""
    decisions: list[Element] = []
    for draft in decision_drafts:
        if not draft.decision_text:
            diagnostics.warn(
                _GENERATOR_NAME, f"Decision draft for round {draft.round_label!r} has no text"
            )
            continue
        if draft.editor_name is None and draft.associate_editor_name is None:
            diagnostics.info(
                _GENERATOR_NAME,
                f"No editor/associate-editor identity available for the round "
                f"{draft.round_label!r} decision (ICAM gap, not fabricated) — "
                f"BR-110's generated summary sentence is not attempted",
            )
        if draft.decision_date is None:
            diagnostics.info(
                _GENERATOR_NAME,
                f"No decision_date available for round {draft.round_label!r}; "
                f"no <date> element emitted",
            )

        review = builder.create_root(
            "review",
            attributes={"review-version": draft.round_label, "review-type": _DECISION_TYPE},
        )
        item_group = builder.create_element(review, "review-item-group")
        add_review_item(
            builder,
            item_group,
            item_type="decision",
            title=config.decision_review_item_title,
            data=draft.decision_text,
            data_type=config.review_item_data_type,
        )
        if draft.editor_name:  # BR-112/113 — only emitted when a real name is available
            add_reviews_contrib(builder, review, "editor", draft.editor_name, "")
        if draft.associate_editor_name:
            add_reviews_contrib(
                builder, review, "associate-editor", draft.associate_editor_name, ""
            )
        decisions.append(review)
    return tuple(decisions)
