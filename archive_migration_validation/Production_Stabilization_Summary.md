# Production Stabilization & Engine Stabilization — Summary

Stabilization milestone, not a feature milestone. No redesign, no
architecture change, no Business/Recovery Rule modified. Every fix is a
small, localized correction at the exact point a confirmed defect was
introduced; see the companion documents for full detail.

## What changed (code)

| Work Item | Change | Files |
|---|---|---|
| 1. Journal prefix crash | Case-insensitive lookup, single normalization point | `service/worker.py` |
| 2. Author-notes data loss | Every block collected and merged (not just the last); dedup now requires byte-identical content, not just a matching id | `generators/article_xml/generator.py`, `generators/xml/helpers.py` |
| 3. Source-data misclassification | Corrupt/missing/empty archives wrapped into the engine's own existing exception types instead of propagating raw stdlib exceptions | `providers/input.py` |
| 4. Recovery reporting gap | A skipped-file recovery with no filename/round/category still gets a real, non-fabricated identifier (its position among declared entries), so it's no longer silently dropped from `missing_files` | `extraction/file_resolver.py` |

Full detail: `Engine_Defects_Fixed.md`, `Source_Data_Classification.md`.

## What was investigated only, no code changed

- **Empty reviews.xml** (43/60 articles): recommend Option B — skip the
  file (and its manifest entry) when no review/decision data exists.
  Not implemented; a real product decision + bounded code change.
- **award-group DTD ordering** (`bst-2025-3027`, `etls-2025-3007`):
  root-caused to a source schema-version mismatch (source uses
  JATS constructs — `award-desc`, `award-id-type` — this DTD variant
  predates), not an engine defect. No fix proposed.
- **award-id-type classification**: recommend remaining
  `Validation Only` — no lossless fix exists, and a rename would now
  collide with a different, already-valid attribute on the same
  element (newly confirmed this milestone).

Full detail: `Product_Decision_Recommendations.md`.

## Verification (lightweight)

101 targeted unit tests (new/changed behavior only) + full suite (1145
passed, 3 pre-existing unrelated failures) + one full 97-article batch
run. Result: `engine_failure` dropped from 5 to 0 across the corpus; the
2 remaining failures are both genuine, correctly-classified source-data
problems. No article that previously succeeded regressed. Full detail:
`Verification_Summary.md`.

## Expected-result checklist

- Journal lookup is robust — ✅ verified (4 previously-crashing articles
  now succeed).
- No author-notes are lost — ✅ verified (14/14 footnotes preserved for
  `cs-2024-5002`).
- Source package failures are correctly classified — ✅ verified
  (`engine_failure: 0`, both remaining failures are `fatal_failure`).
- Recovery reports are more informative — ✅ verified (`bst-2025-3095`'s
  `missing_files` now populated).
- Engine failures only represent genuine engine defects — ✅ (0 in the
  full-corpus run).
- Product decisions documented separately from code — ✅
  (`Product_Decision_Recommendations.md`, no implementation).
- Existing package generation behavior unchanged except for the
  confirmed defect fixes — ✅ verified (no regressions in the
  full-corpus run).
- No architectural redesign, no unnecessary refactoring, no fabricated
  metadata, no excessive documentation — ✅ (5 documents produced, as
  scoped).
