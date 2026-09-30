# Business Rule Recommendations

Analysis only — no Business Rule Book entry, ADR, or code was changed as
part of this document. Every classification below is grounded in the
bcj-2025-3130 manual-QA investigation (20 findings, root-caused against
real source XML, real generated output, and the actual running
generator/extraction code) plus the confirmed-but-unfixed defect
uncovered while implementing Milestone 1. Categories and recommended
treatments follow the taxonomy given in this milestone's brief.

## Classification legend

| Category | Meaning |
|---|---|
| Confirmed Business Rule | Already correctly implemented; QA finding was a false positive against current spec |
| Missing Business Rule | No rule exists for this case; the engine's current behavior is spec-compliant by omission, not defective |
| Recovery Rule | A gap the engine should paper over deterministically and flag, not fail on |
| Source Data Issue | The publisher's own XML is malformed/incomplete; engine faithfully reproduced it |
| Engine Defect | The engine has the correct data available and drops/misplaces it |
| Publisher Variation | A publisher-specific export quirk, not a defect in either the spec or the engine |
| Journal Specific Rule | Behavior that should be configurable per journal rather than global |

## article.xml findings

| # | Finding | Classification | Recommended treatment |
|---|---|---|---|
| 1 | `abbrev-journal-title[@abbrev-type="publisher"]` missing | Source Data Issue | None — inventing this value would fabricate publisher data. No rule change. |
| 3 | `<degrees>` contains email+ORCID+counters concatenated | Source Data Issue / Publisher Variation | Warning-only Recovery Rule: flag `<degrees>` content that fails a simple "looks like a person's academic degree" shape check, without altering it. Mandatory: never auto-clean. |
| 4 | Associate-editor `<contrib>` rows duplicated inside the author `contrib-group` | Source Data Issue | None — duplication exists in source itself, in both groups consistently. No rule change; optionally a Warning-only Recovery Rule noting cross-group duplication for manual review. |
| 5 | `contrib-type="submitting-author"` not emitted | **Missing Business Rule → now a Confirmed Business Rule** | Implemented in Milestone 1 (`_build_submitting_author_contrib_group`). Recommend formalizing as a new Business Rule Book entry (e.g. BR-165) so it's no longer undocumented. |
| 6 | Corresponding-author affiliation text missing | Source Data Issue | None — source `<corresp>` has no address data to copy. |
| 7 | `data-type="figshare-statement"` not renamed to `content-type` | Missing Business Rule | Recommend a new, explicit Business Rule authorizing this one renormalization (publisher-attribute → JATS-attribute), scoped narrowly to this attribute/value pair — do not generalize to a blanket "rename all data-* attributes" rule without further corpus evidence. Journal Configuration if this pattern turns out to be journal-specific. |
| 8/9 | Per-role footnotes and consolidated CRediT paragraph both present | Confirmed Business Rule | None — both are independently authored in source; current pass-through behavior is correct. |
| 9b | Reported "unwanted text" (`â€™`) | Confirmed Business Rule (false positive) | None — file is correctly UTF-8 encoded; the artifact is a display/tooling issue outside the engine. Recommend noting this in reviewer-facing documentation so it isn't re-reported. |
| 10 | Reviewer `contrib-group` positioned after `</abstract>` instead of before | **Engine Defect → fixed** | Fixed in Milestone 1 (`_build_article_meta` contrib-group clustering). No further action. |
| 11/12/13 | epub/ppub, volume/issue, fpage/lpage missing from article.xml | **Engine Defect → fixed** | Fixed in Milestone 1 (extended `_COPIED_VERBATIM_TAGS`). Recommend a regression test asserting these 5 tags are always copied when present in raw.xml, to prevent silent re-regression. |
| 14 | Figure/supplement `custom-meta` entries missing for the "R1" round | **Engine Defect → confirmed, not yet fixed** | See "Confirmed-but-unfixed defect" below. Mandatory fix, but requires extraction/round-resolution changes outside this milestone's generator-only scope. |

## reviews.xml findings (1–6)

All six items trace to the same, single, already-documented decision
(`review_builder.py`'s own docstring, citing the Reviews Decision Log):
scorecard extraction was deliberately scoped to flattened `<string-name>`
and blob-text answers because, at the time that decision was made, none
of the 3 real reference packages carried structured reviewer names,
recommendation, or per-question data.

| Classification | Recommended treatment |
|---|---|
| Recovery Rule (as currently implemented) | Current behavior — flatten to `<string-name>`, leave recommendation/dates `None` — is a deliberate, documented Recovery Rule, not a defect. No immediate code change recommended. |
| Missing Business Rule (worth revisiting) | bcj-2025-3130 disproves the "3 references" assumption: its source *does* carry structured `<name>`, a real recommendation signal (`data-reviewer-message`), and per-question answers. Recommend a follow-up corpus review (broader than 3 samples) to decide whether reviews.xml extraction scope should be widened — this is a scope decision for the Business Rule Book owners, not an engine defect to silently fix. |

## Confirmed-but-unfixed defect: figure/supplement custom-meta (item #14)

- **Root cause**: `extraction/round_resolver.py` (ADR-013) recognizes
  rounds strictly by `<article-version>`/vocab-identifier matching
  (`"snapshots/<N>_..."`), independent of the file-manifest's own round
  labels. bcj-2025-3130's file manifest carries entries under round
  label `"R1"`, which the round resolver does not recognize as a valid
  round at all — so 16 of 18 file_entries (including all 12 figures)
  are silently excluded before article.xml generation ever runs.
- **Why not fixed in this milestone**: the fix belongs in
  extraction/round-resolution, not the article.xml generator. Milestone
  1's explicit scope is "do not modify extraction, fix only the
  generator." A generator-only workaround would require re-implementing
  round-ordering logic already owned by `round_resolver.py` — directly
  against this program's "do not create duplicate implementations"
  constraint.
- **Recommendation**: Engine Defect, Mandatory fix, dedicated follow-up
  milestone. `round_resolver.py` should recognize file-manifest round
  labels (e.g. `"R1"`) as an equally valid round signal alongside
  `<article-version>`, or explicitly document why the two are allowed to
  diverge. This is a correctness gap, not a style preference — until
  fixed, every article whose file manifest uses a round label the
  `<article-version>` vocabulary doesn't recognize will silently drop
  file entries.

## Summary table

| Category | Count | Items |
|---|---|---|
| Confirmed Business Rule (already correct) | 5 | #4, #6, #8, #9, #9b |
| Missing Business Rule (recommend adding) | 2 | #5 (now implemented), #7 |
| Recovery Rule (deliberate, documented) | 6 | reviews.xml #1–#6 |
| Source Data Issue (no action) | 4 | #1, #3, #4 (dup), #6 |
| Engine Defect — fixed this milestone | 3 | #10, #11/12/13 |
| Engine Defect — confirmed, unfixed | 1 | #14 |
| Publisher Variation | 1 | #3 (`<degrees>` shape) |
| Journal Specific Rule (candidate) | 1 | #7, pending corpus evidence |

No Business Rule Book entry, ADR, or Recovery Rule was modified to
produce this document. All recommendations above require separate,
explicit approval before implementation.
