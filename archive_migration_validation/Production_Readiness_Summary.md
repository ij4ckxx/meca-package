# Production Readiness Summary — Final Milestone

Stabilization-only milestone, as scoped: no architecture change, no new
framework, no status-model change, no Business/Recovery Rule content
rewritten. Every fix is a small, localized correction at the exact point
a confirmed defect was found; every finding without a safe, minimal fix
is documented instead of implemented. Full detail: `Production_Findings.md`.
Verification: `Production_Verification.md`. Operator-facing changes
folded into the existing `Operator_Guide.md` in place (no separate
duplicate guide) — the certified-fix and Dashboard sections there are
updated to match this milestone's code changes.

## What changed (19 fixes, all with regression tests)

**Reliability / "never stop the batch"**
- A last-resort safety net now guarantees one article's exception can
  never end the whole run, even a bug in the Worker's own error handling.
- Every raw exception path found (asset-copy/zip-write failures,
  post-build re-validation) is now wrapped into the engine's existing
  exception hierarchy instead of surfacing unclassified.

**Correct classification**
- Exhausted-retry infrastructure failures (S3, DOI registry, checkpoint
  store) now correctly report `ENGINE_FAILURE`, not `FATAL_FAILURE`.
- 25 articles' `ID con<N> already defined` DTD findings now correctly
  classify as `source_data_issue` instead of the `validation_only`
  default.

**"Safe to operate for weeks"**
- Fixed a real temp-directory leak: every article's extraction was never
  cleaned up, on any outcome — would have filled local disk over a
  large, long-running batch.
- The Dashboard's data source (`conversion_reports.json`) now refreshes
  every 25 articles during a run instead of sitting empty until the
  whole batch finishes.
- Restarting a narrower subset under the same batch id no longer
  silently drops every other article's record from the aggregate report
  (confirmed by direct reproduction, then fixed).

**Performance (safe, no redesign)**
- DTD files no longer re-parsed from disk on every single validation —
  cached per batch (~400,000 redundant re-parses eliminated at 100k-
  article scale).
- The reproducibility config-checksum is now computed once per batch,
  not once per article.

**Transparency / operator understanding**
- Per-article failures are now logged at ERROR severity (previously
  silent in the log stream, visible only in written report files).
- The Certification Report — the first report an operator opens for a
  failed article — now shows the real, specific failure reason instead
  of a generic template sentence.
- Fixed a Dashboard bug where warning counts undercounted (excluded
  generator-level findings) and, on the detail page, weren't populated
  at all; the Warnings tab now shows every finding; the failure reason
  is a readable message instead of a raw object dump.

**Data-quality safety net**
- Closed a confirmed (if latent) file-substitution risk in Recovery Rule
  RR-004's fuzzy filename matching, where a free-text declared label
  could be misparsed and match the wrong physical file.

**Housekeeping**
- Corrected two pre-existing clerical errors in `01_BUSINESS_RULE_BOOK.md`
  (stale Priority-total arithmetic, a Section K heading typo) — no rule
  content changed.

## Verification

101+ new/extended targeted tests, full suite (1161 passed, same 3
pre-existing unrelated golden-snapshot failures every prior milestone
has also reported), one full 97-article batch run — identical
package-generation outcome to the prior milestone's final run
(`engine_failure: 0`, 95/97 packages, 2 correctly-classified fatal
failures). `ruff`/`mypy --strict` clean on every changed Python file;
`tsc --noEmit` clean on both dashboard packages.

## Recommendations requiring a separate decision

1. **Empty `reviews.xml` (Option B)** — you've already indicated this
   product decision: omit `reviews.xml` (and its `manifest.xml` entry)
   when an article has zero review/decision data, rather than shipping
   an empty, DTD-invalid file. This was **not implemented in this
   milestone** — it's a real, if bounded, code change (making
   `PackageBuilder`'s currently-fixed 5-generator sequence conditional
   for this one file, and giving `manifest_xml` the same "has review
   content" check `reviews_xml` already computes), not a defect fix,
   and this milestone's scope was defect-fixing/stabilization only. Say
   the word and I'll implement it as its own focused change, with its
   own regression tests and verification run.
2. RR-003/RR-007's structural reporting gap (dormant, zero real
   firings so far) and the source-XML-`ParseError` misclassification
   (Item 2) both need a dedicated, careful follow-up — not urgent, but
   real.
3. Two Dashboard UX gaps (list pages missing a DTD-status column;
   Manual Review Reason too thin) — cosmetic, worth a small follow-up
   pass, not stabilization-critical.

Full reasoning for every recommendation is in `Production_Findings.md`.

## On convergence

Confirmed again this milestone: the corpus-wide re-verification shows
`engine_failure: 0` and identical package-generation behavior to the
prior milestone's run, even after this pass's much broader raw-exception
and failure-classification review — no new defect class was found that
changes that picture. The remaining open items are genuinely either
product decisions (reviews.xml) or narrow, low-probability edge cases
with no observed real-world impact yet (RR-003/007, the ParseError
path) — consistent with a converging, production-ready engine rather
than one still surfacing new defect classes.
