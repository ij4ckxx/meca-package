# Final DTD Compliance Summary — Specification-Alignment Milestone

> **Superseded by the Business Rule Completion milestone**: all 3
> Business Rule Candidates below (data-type, xref/@rid, reviews.xml
> structured names) are now implemented as BR-161/162/163. The
> "after" DTD-compliance numbers in this document reflect the state
> *before* that milestone — see the Business Rule Completion summary
> for the current, much-improved corpus-wide DTD pass rate
> (article.xml 0→19/37, reviews.xml 0→33/37).

## What this milestone was

Not a bug-fixing exercise — a full classification of every DTD
violation the engine currently produces across the entire 37-article
corpus, sorted into exactly one of 5 categories *before* any code was
touched, with only Category A (Safe Engine Defect) actually fixed.
Everything else stays documented, visible, and unimplemented pending
approval.

## Result, in one paragraph

Every one of 951 DTD findings produced against the real corpus was
individually investigated and classified. Two were confirmed, safe,
lossless engine defects and fixed: 9 content-free duplicate `aff`
stubs dropped (of 16 total duplicate-id cases — the other 7 carry
genuinely distinct data and were deliberately left alone), and a
corrupted internal id unconditionally stripped from `journal-meta`
(confirmed, corpus-wide, to never be a cross-reference target). The
remaining 942 findings break down as 924 Business Rule Candidates (3
proposals, all deterministic and lossless, none implemented), 20
Validation Only (cannot be safely repaired without an assumption), and
7 Source Data Issue (the source itself assigns one id to two different
real facts). No publisher data was fabricated, cleaned, or silently
dropped anywhere in this milestone.

## Corpus-wide DTD compliance, before → after

| File | Before this milestone | After |
|---|---|---|
| manifest.xml | 37/37 DTD-valid | 37/37 DTD-valid (unchanged) |
| transfer.xml | 37/37 DTD-valid | 37/37 DTD-valid (unchanged) |
| article.xml | 0/37 DTD-valid | 0/37 DTD-valid — but "ID already defined" now 7/37 (was 16/37), all remaining findings classified |
| reviews.xml | 0/37 DTD-valid | 0/37 DTD-valid — unchanged (its one defect, `<string-name>`, is a proposed Business Rule, not an engine defect) |

No file type regressed. article.xml's error *count* dropped for every
one of the 9 fixed articles; its DTD-valid *pass rate* is unchanged
because every article still has at least one Business Rule Candidate
finding (the `data-type`/`rid`-separator issues affect all 37) — those
require approval, not code, to resolve. Full detail per category in
`DTD_Fix_Summary.md` and `Remaining_Validation_Issues.md`.

## Category breakdown (final corpus-wide totals)

| Category | Count | Disposition |
|---|---|---|
| A — Safe Engine Defect | 2 defect *types* (25 individual duplicate/corrupted-id instances) | Fixed |
| B — Source Data Issue | 7 | Documented, surfaced, not changed |
| C — Business Rule Candidate | 924 | 3 proposals written, none implemented |
| D — Recovery Rule Candidate | 1 candidate evaluated | Not recommended (orphaning risk) |
| E — Validation Only | 20 | Documented, surfaced, not changed |

## Batch execution

Full run against `Input/` (37 articles), re-run 4 times across this
milestone as the investigation and fixes progressed (`spec-alignment-baseline`
→ `-final` → `-final-2` → `-final-3` → `-final-4`, the final one being
authoritative):

```
Total: 37
  certified_with_warnings: 3
  certified_with_recovery: 30
  partial_certification: 4
  engine_failure: 0
  fatal_failure: 0

Packages generated: 37/37
Total warnings: 0
Total recoveries: 213
Engine failures: 0
Fatal failures: 0
```

Identical across every run — package generation behavior was never
affected by anything in this milestone, exactly as required.

## Test suite

`pytest tests/`: **1135 passed, 3 failed.** The 3 failures are the
same pre-existing, unrelated golden ICAM snapshot mismatches
(affiliation `country`/`institution` fields) documented in every prior
milestone's summary — a code path this milestone never touches.

## Dashboard

Extended, not redesigned: the existing validation pages/sections
(Article Detail's "XML Validation" tab, Home's validation widgets,
Analytics' validation charts) now also show, additively:
- "Engine Defects Fixed" count (computed from `generator_findings`
  matching known fix-message prefixes — no new engine-side field)
- Category counts (Source Data Issue / Business Rule Candidate /
  Recovery Rule Candidate — computed from each issue's new
  `category` field)
- Remaining DTD violation totals
- Per-issue category tags in the Article Detail validation tab

Verified live against the real `spec-alignment-final-4` batch through
the running dashboard dev server: `/api/summary` and
`/api/analytics/validation` both correctly report
`spec_alignment_counts: {business_rule_candidate: 924, validation_only: 20,
source_data_issue: 7}` and `engine_defects_fixed_count: 574`.

## Constraints honored

`PackageBuilder`, Certification, Processing Service, Recovery
philosophy, and dashboard architecture were not modified. The only new
module is `validation/dtd_issue_classifier.py` (a lookup table, not a
framework) — every other change extends an existing module
(`generators/article_xml/generator.py`, `generators/xml/helpers.py`,
`validation/models.py`, `validation/xml_validator.py`,
`reporting/validation_report.py`, the existing dashboard pages).

## Deliverables

1. `DTD_Fix_Summary.md`
2. `Remaining_Validation_Issues.md`
3. `Proposed_Business_Rules.md`
4. `Proposed_Recovery_Rules.md`
5. `Final_DTD_Compliance_Summary.md` (this document)

## Newly discovered, out-of-scope finding

article.xml has no `<ref-list>`/`<back>` bibliography section at all
in the current corpus — 4/37 articles have in-text citations
(`xref[@ref-type="bibr"]`) pointing at reference ids that consequently
don't exist anywhere in the document. This surfaced only because those
4 citations happen to live inside verbatim-copied `author-notes`
content; the underlying gap (no reference-list generation at all) is
likely broader than these 4 DTD errors suggest. Flagged for a
dedicated future investigation — implementing bibliography generation
is a substantially larger effort than this milestone's "minimum
necessary changes" scope, not a spec-alignment classification item.
