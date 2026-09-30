# Quality Improvement Summary — Final Milestone

Mission: generate the highest-quality MECA package possible without
fabricating publisher data. No architecture, dashboard, reporting,
Processing Service, provider, or performance work touched — XML
generation quality only, as scoped.

## What was done

A fresh, from-scratch investigation (not assuming any prior milestone's
findings remain complete) compared, for every one of the 97 articles in
the current corpus: source XML vs. generated XML vs. the official
vendored NISO MECA DTD suite and JATS Archiving 1.2 DTD suite vs. the
Business Rule Book vs. the Recovery Rule catalog. Four parallel
investigation agents were launched for this; all four were cut off
mid-investigation by an account-level rate limit. Rather than lose the
work, the investigation continued directly — corpus-wide scripted
checks (ID uniqueness across all 5 files, IDREF/xref resolution,
manifest-to-zip consistency, and targeted source-vs-generated
content-fidelity comparisons for ORCID/keywords/permissions/dates/
funding/corresponding-author data) across all 95 real generated
packages, not a sample.

## What was found: one real engine defect (Category A)

`bsr-2025-3821`'s declared figure `"Fig.3a-f"` was silently packaged
with the **wrong image's bytes** (`Fig.2.tif`'s content, not the missing
`Fig.3a-f.tif`) — a mis-parse in a filename-matching guard from a prior
milestone treated `".3a-f"` as a plausible file extension, truncating
the declared name to `"fig"`, which then loosely prefix-matched an
unrelated file. This is arguably the most serious content-fidelity
defect found across this entire engagement: DTD validation could never
catch it (each file is individually well-formed either way), and the
package looked completely successful (`certified_with_recovery`) while
silently misattributing a figure. Fixed with a precise, minimal guard
(a real extension must be alphabetic); the correct outcome is now an
honest "file missing" report (`partial_certification`), matching what's
actually true of the source. Full detail: `Engine_Defects_Fixed.md`.

Every other structural/ID/IDREF/manifest-consistency check performed
corpus-wide came back clean.

## What was re-confirmed: zero new Business or Recovery Rules

All 12 distinct DTD finding patterns present in the corpus were
independently re-derived from first principles. Every one still fails
the same bar every Business/Recovery Rule in this engine must clear
(deterministic, lossless, no fabrication) — full reasoning per pattern
in `New_Business_Rules.md`. This is treated as a meaningful, positive
result: three prior milestones of rule-book development already cover
every real pattern in the current corpus.

## Final Report

| Metric | Value |
|---|---|
| Packages processed | 97 (95 packages generated, 2 fatal failures) |
| Engine defects fixed | 1 (Category A — `bsr-2025-3821` wrong-file substitution) |
| New Business Rules | 0 (12 candidate patterns re-evaluated, none cleared the deterministic/lossless bar) |
| New Recovery Rules | 0 (none found; all recoverable gaps already covered by RR-001/002/004) |
| Source Data Issues (Category D) | 5 distinct patterns, 49 articles total (`Remaining_Source_Data_Issues.md`) |
| Validation Only findings (Category E) | 7 distinct patterns, spanning up to 47 articles each (`Remaining_Validation_Findings.md`) |
| DTD compliance before → after | `{error: 91, pass: 4}` → `{error: 91, pass: 4}` (unchanged — the fixed defect was invisible to DTD structural validation by construction) |
| Remaining manual-review articles | 10 `partial_certification` (up 1 — the newly, honestly reclassified article), 2 `fatal_failure` (pre-existing, unrelated) |
| Package-generation behavior | Unchanged except the one deliberate correction — confirmed via full before/after corpus diff (exactly 1 status change, 0 unintended side effects) |

## Recommendation carried forward (unchanged, still pending your decision)

The empty-`reviews.xml` Option-B product decision remains implemented-
but-not-yet-coded, per your own prior direction to treat it as a
separate, deliberate follow-up rather than bundle it into a
stabilization/quality milestone. Say the word and it's a focused,
bounded change with its own tests and verification run.
