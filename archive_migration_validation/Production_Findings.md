# Production Findings — Final Production Readiness Milestone

Organized by the 13 review items in scope. Each finding is marked
**[FIXED]** (confirmed engine defect, corrected this milestone),
**[RECOMMEND]** (documented, not implemented — needs a follow-up pass or
a product decision), or **[VERIFIED, NO ACTION]** (reviewed, found
correct as-is).

## 1. Production Stability Review (raw exceptions)

- **[FIXED]** `providers/input.py`'s `LocalInputProvider.stage_article()` let
  `zipfile.BadZipFile`/`FileNotFoundError` escape unwrapped, always
  misclassified as `ENGINE_FAILURE` by the generic catch-all downstream.
  Now wrapped into `SourceUnavailableError`/`InvalidArticlePackageError`
  (prior milestone's fix, still in effect).
- **[FIXED]** `packaging/builder.py`'s own docstring promised
  `PackageAssemblyError: On any asset-copy or zip-write failure`, but its
  `except BaseException: ...; raise` re-raised the raw exception
  unwrapped — a disk-full/permission error during asset copy or zip
  writing (`asset_copy.py`, `zip_builder.py`) surfaced unclassified.
  Fixed at the one existing cleanup boundary: any `Exception` that isn't
  already a `MecaEngineError` is now wrapped into `PackageAssemblyError`;
  `KeyboardInterrupt`/`SystemExit` are deliberately never wrapped, so an
  operator can still cleanly stop a run.
- **[FIXED]** `validation/package_validator.py`'s `validate_staged_package()`
  documents itself as "never raises," but its `zipfile.ZipFile(...)` open
  wasn't guarded — an already-successfully-built package could be turned
  into a false `ENGINE_FAILURE` report by a transient re-validation
  hiccup. Now returns an empty validation report on any
  `OSError`/`BadZipFile`, honoring its own contract.
- **[RECOMMEND]** `orchestrator/run_controller.py`'s pipeline only catches
  `ArticleLevelError` (narrower than `MecaEngineError`) — but confirmed
  **not wired into the live batch-conversion path**
  (`scripts/archive_migration_batch.py` → `service_factory` → `Worker`
  never references `run_controller`/`container`). Left as-is: fixing a
  legacy/superseded pipeline isn't a priority to touch under this
  milestone's "minimal changes" scope.
- **[RECOMMEND]** `config/loader.py` has one unwrapped `json.load()` for
  the config-schema file itself. Batch-startup only (not per-article) —
  a broken schema file fails loudly and immediately, before any article
  is processed, so the operational risk is low. Recommend wrapping in a
  future pass for consistency.

## 2. Failure Classification Review

- **[FIXED]** `service/worker.py`'s `_classify_failure()` didn't include
  `ArticleTransientError` (S3 read/write, DOI-registry, checkpoint-store
  outages, staging/post-write integrity mismatches) in
  `_ENGINE_DEFECT_EXCEPTION_TYPES`. Once `run_with_retry` exhausts every
  retry attempt on one of these, it was reported as `FATAL_FAILURE`
  ("the source data itself made safe recovery impossible") — the
  opposite of the truth (a sustained infrastructure outage, explicitly
  documented as retryable/not-the-data's-fault in each subclass's own
  docstring). Fixed: `ArticleTransientError` added to the engine-defect
  tuple, so an exhausted-retry infra failure is now `ENGINE_FAILURE`.
- **[FIXED]** `DoiCollisionError`'s docstring claimed routing to "the
  human-review queue by `meca_engine.recovery`" — but `recovery/` is an
  empty, deliberately-unimplemented stub (documented as such in its own
  module). No such queue exists; the exception is (correctly) classified
  `FATAL_FAILURE` and routed to `failed/` like every other fatal failure.
  Docstring corrected to state this accurately.
- **[VERIFIED, NO ACTION]** `packaging/builder.py`'s `_compute_status()`
  (the `CERTIFIED`/`..._WARNINGS`/`..._RECOVERY`/`PARTIAL_CERTIFICATION`
  decision) matches `PackageStatus`'s own documented decision order
  exactly — no divergence found.
- **[RECOMMEND]** A source-document `ParseError` during `raw_xml`'s
  re-parse of a reserialized body fragment (real, source-derived text —
  not the already-validated ICAM) is caught by `generators/base.py`'s
  catch-all and reported as `GeneratorInvariantError` → `ENGINE_FAILURE`,
  even though the true cause is malformed source content (stray control
  characters surviving from a Word-sourced submission, for example) —
  arguably `SourceXmlMalformedError` → `FATAL_FAILURE` instead. Not fixed
  this milestone: correctly scoping this reclassification to *only* this
  one re-parse site (without weakening the catch-all's protection for
  genuine generator-invariant violations elsewhere) needs careful,
  dedicated work.

## 3. DTD Validation Completion

Every distinct DTD finding across the full 97-article corpus was
reviewed against the classifier's 4-category taxonomy:

- **[FIXED]** `ID con<N> already defined` (25/97 articles, ~388
  occurrences) fell through to the `VALIDATION_ONLY` default because the
  classifier's duplicate-id pattern was scoped to `(aff|cor)` prefixes
  only. Root-caused: some sources repeat the same CRediT role code
  (`con1`..`con14`) with genuinely different text across separate
  editorial rounds, and `raw_xml`'s cleanup XSLT promotes that role code
  to the literal XML id — a source-side collision, not an engine bug
  (the already-fixed author-notes-merge logic correctly keeps all of
  them, since dropping any would risk misattributing a contribution).
  Reclassified to `source_data_issue`, prefix-agnostic (broadened to any
  `ID \S+ already defined`, since the reasoning doesn't depend on prefix).
- **[VERIFIED, NO ACTION]** `award-id-type` (26/97 articles): re-confirmed
  no lossless rename target exists — the same `<award-id>` already
  carries a valid, different `award-type` attribute, so a rename would
  overwrite real data. Stays `VALIDATION_ONLY`.
- **[VERIFIED, NO ACTION]** Empty `reviews.xml` (47/97): confirmed
  genuine zero-review-history source data, not an extraction gap. Stays
  `VALIDATION_ONLY` pending the Option-B product decision (see summary).
- **[VERIFIED, NO ACTION]** `award-group`/`award-desc` (2/97): confirmed
  source uses a newer JATS funding profile than this DTD variant
  declares (schema-version mismatch) — a `DTD limitation` (category E),
  documented only, source content never altered.
- **[VERIFIED, NO ACTION]** `<fn><list>` flattening, dangling `bibr`/`aff`
  xrefs, `string-name`/`name-alternatives`, `ext-link`/`p` attribute
  findings — all previously catalogued, re-confirmed unchanged.

## 4. Generator Review

Read `article_xml`, `reviews_xml` (+ `review_builder`/`decision_builder`),
`manifest_xml`, `transfer_xml` in full, cross-checked against DTD content
models, the Business Rule Book, and real generated packages.
**No new confirmed engine defects found** beyond what Items 1-3 already
cover. One product-decision candidate surfaced (not a defect — the
generator behaves exactly as documented):

- **[RECOMMEND — product decision, not a defect]** `_resolve_license_type()`
  defaults to synthesizing a CC-BY-4.0 `<license>` whenever source has
  **no** license-type key at all (not only when one explicitly says
  CC-BY) — already flagged in the generator's own docstring as "pending
  explicit business confirmation" (BR-065). Now has a concrete corpus
  count: 2/95 generated packages hit this exact case.

## 5. Dashboard Review

- **[FIXED]** Article list view's `warning_count` excluded
  `generator_findings`, undercounting relative to every Python-side
  report (Certification Report, Batch Audit Report, corpus analyzer) —
  a real article (`CS-2024-2165`) showed "Warning Summary (4)" in its
  Certification Report but "0" and an empty Warnings tab on the
  Dashboard. Fixed in `dataStore.ts` (list) — now matches the Python
  convention exactly.
- **[FIXED]** Article detail view's `warning_count`/`recovery_count` were
  never actually populated by the server at all (a deeper version of the
  same gap — `getArticle()` never set them, so the detail page's stat
  line rendered `Warnings (undefined) / Recoveries (undefined)` for
  every article). Fixed alongside the above.
- **[FIXED]** Warnings tab only rendered `warnings`, never
  `generator_findings` — now shows both.
- **[FIXED]** Failure reason rendered `JSON.stringify(data.unrecoverable_error)`
  — now shows the real message + stage, typed properly instead of an
  untyped `Record<string, unknown>`.
- **[RECOMMEND]** Manual Review Reason is thin (bare rule ids, no
  filename) and its message-building logic is duplicated slightly
  inconsistently between server (`describeReason`) and client
  (`ArticleDetailPage.tsx`). Recommend consolidating into one
  server-side builder in a future pass.
- **[RECOMMEND]** Confidence score doesn't factor in DTD/validation
  results (by design — advisory only, documented as such) — a "100%
  confidence, real DTD error" combination is possible and not obviously
  flagged as a separate axis on the stat card. Not a code fix (would
  touch the confidence-score model, out of this milestone's scope);
  addressed with one clarifying line in the Operator Guide instead.
- **[RECOMMEND]** Articles/Migration Audit list pages don't show a
  DTD/validation status column (only available on the detail page) —
  worth adding in a future UI pass; not implemented here to avoid a
  layout change under this milestone's "no redesign" scope.

## 6. Reporting Review

- Root cause of every cross-report inconsistency found traced back to
  the single Item 5 `warning_count` gap above (now fixed) — with that
  fixed, the Certification Report, Batch Audit Report, and Dashboard all
  agree on warning/recovery counts for every article checked.
- **[VERIFIED, NO ACTION]** Status, confidence score, and recovery
  rule/count agree identically across Certification Report, Validation
  Report, Migration Audit Report, `conversion_reports.json`, and the
  Dashboard for every article sampled.

## 7. Recovery Rule Review

- **[FIXED]** RR-004's "prefix" tolerance tier computed
  `Path(declared_name).stem`, which mis-parses a free-text declared label
  containing one embedded, non-trailing "." (not a real
  `<name>.<ext>` pair) into a near-meaningless 1-2 character stem —
  confirmed on real data (`CS-2025-6808`'s `"1.manuscript highlight
  yellow 1"`) that this could then prefix-match an unrelated physical
  file. Fixed with a targeted guard: the declared name is only treated
  as having a real extension if the tail looks like one (short, no
  spaces); otherwise the whole label is used as the stem. Confirmed this
  doesn't change any real match in the current corpus (the one
  real-world case actually resolves via the safer "stem" tier first) —
  purely closes a latent substitution risk.
- **[VERIFIED, NO ACTION]** RR-001, RR-002, RR-005, RR-006: confidence
  levels, losslessness, and safety all confirmed appropriate against
  real firing evidence across the corpus.
- **[RECOMMEND]** RR-003/RR-007's call sites only ever call
  `diagnostics.warn(...)` (a `GeneratorDiagnostic`, not an
  `EngineWarning`) — they can never appear in `ConversionReport.recoveries`
  or be scored via the documented missing-metadata bucket, despite
  `_MISSING_METADATA_RULE_IDS` claiming all three (RR-003/006/007) are
  scored identically. Confirmed dormant: 0 real firings across the full
  97-article corpus, so no observed impact yet. Recommend routing both
  through a proper `EngineWarning` in a dedicated follow-up, not fixed
  here given zero real-world exercise of this path so far.

## 8. Business Rule Review

- **[FIXED]** `01_BUSINESS_RULE_BOOK.md`'s own "Rule Count Summary"
  Priority totals were stale/wrong (stated Critical 46/High 65, actual
  count from the document's own rule text is Critical 61/High 50) —
  corrected. Section K's heading also said "BR-161 – BR-162" while
  documenting through BR-163 — corrected to match.
- **[VERIFIED, NO ACTION]** Spot-checked 20 rules across sections
  A-K — all match documented behavior. No dead rules found. BR-012/
  BR-023 and BR-089/BR-153 are near-duplicate pairs, but both are
  already explicitly self-acknowledged as intentional restatements in
  the Book's own text — no action needed. The 6 tracked Business Rules
  (`_TRACKED_BUSINESS_RULE_IDS`) all fire as expected against real
  corpus data.

## 9. Performance Review

- **[FIXED]** `validation/xml_validator.py` re-parsed the same vendored
  DTD file from disk on every single validation call — up to ~400,000
  redundant re-reads/recompiles across a 100,000-article batch (DTD
  files never change within a run). Now cached (`functools.cache`) —
  `etree.DTD` objects are read-only and safe to reuse across
  validations.
- **[FIXED]** `reporting/reproducibility.py`'s config-checksum
  (SHA-256 over a deep recursive dataclass walk) was recomputed on every
  article even though `RuntimeConfig`/`FeatureFlagsConfig` never change
  within a batch. Now computed once (lazily, on first real use) per
  `Worker` instance and reused.
- **[FIXED, this milestone's own regression]** The batch-reliability fix
  in Item 11 (below) initially re-read the whole `conversion_reports.json`
  from disk on every incremental snapshot — refined to load prior
  records once at the start of a run and merge purely in-memory
  thereafter, avoiding repeated disk round-trips.
- **[RECOMMEND]** `extraction/xml_loader.py` parses each XML document
  twice — once for the tree (`_parse_tree`), once more via a separate
  `iterparse` pass just to collect namespace declarations
  (`_collect_namespaces`). Real, confirmed inefficiency, but combining
  both into one pass touches the shared parsing path every document in
  the pipeline goes through — higher regression risk than this
  milestone's "minimal changes" bar comfortably allows. Recommend as a
  dedicated follow-up with its own regression coverage.

## 10. Memory Review

- **[FIXED]** `providers/input.py`'s `LocalInputProvider.stage_article()`
  extracted every article into a fresh `tempfile.mkdtemp()` directory
  that was **never cleaned up** — on any outcome (success, failure, or a
  staging error before a `StagedArticle` was even returned). At
  6,000-100,000 articles this would accumulate full extracted-archive
  copies in the OS temp directory indefinitely, a real risk of filling
  local disk over a multi-week run. Fixed: cleaned up on the error path
  inside `stage_article()` itself, and on every outcome (success or
  failure) via a `try/finally` in `Worker._process_once()`, matching the
  lifecycle an earlier, now-superseded staging framework
  (`input/staging.py`'s `Stager.cleanup()`) already documented and
  implemented, but which this newer provider had silently dropped.
- **[VERIFIED, NO ACTION]** No other unclosed-resource or
  repeated-parsing pattern found beyond what Item 9 already covers.

## 11. Batch Reliability

- **[FIXED]** `conversion_reports.json` — the Dashboard's entire
  per-article data source — was written exactly once, at the very end
  of a batch run. For a batch spanning hours-to-days, the Dashboard
  showed **zero articles** for the run's entire duration, only
  populating everything at the end. Fixed: refreshed every 25 completed
  articles (bounded, atomic write-then-rename) in addition to the final
  write.
- **[FIXED]** Reusing the same `--batch-id` with a narrower
  `--article-ids` subset (the documented "restart just the
  failed/manual-review articles" workflow) **silently discarded every
  other article's record** from `conversion_reports.json` — confirmed
  by direct reproduction (a 3-article batch, followed by a 1-article
  restart under the same batch-id, dropped the other 2 from the
  aggregate JSON, even though their real packages remained correctly on
  disk). Fixed: the write now merges with whatever the file already
  holds, keyed by `article_id`, so a restart only ever updates the
  articles it actually reprocessed.
- **[FIXED]** No per-article failure was ever logged at ERROR severity
  in the structured log stream (only written into report files) —
  `Worker.process()`'s two failure branches now call the existing,
  already-established `logger.log_exception()` convention (already used
  in 3 other modules; simply missing from the live, in-use pipeline).
- **[VERIFIED, NO ACTION]** Batch-never-stops: confirmed via the safety
  net in Item 1/12 below plus re-verification of the full 97-article
  corpus run (0 engine failures, 2 correctly-classified fatal failures,
  97/97 attempted). Checkpoint/resume: the in-memory `CheckpointStore`
  only dedupes within one process's lifetime by design (documented,
  deliberate Milestone-2 scope — a durable backend is explicitly
  deferred, not a defect); "restart a subset" is the supported, already-
  working workaround for a full process restart (`--article-ids`), now
  further hardened by the merge-on-write fix above.

## 12. Operational Review

- **[FIXED]** `Worker.process()`'s two exception branches never called
  the existing `log_exception()` convention (Item 11) — the only visible
  console output for a hard failure was a bare
  `print(f"{article_id}: {status} ({elapsed}s)")` with zero indication
  of *why*.
- **[FIXED]** The Certification Report — the first report an operator
  opens for a failed article, per the Operator Guide's own flow — showed
  only a generic per-status template sentence, never the real,
  specific reason already available on `report.unrecoverable_error`.
  Now shown in a new "Failure Reason" section.
- **[FIXED, safety net]** A genuinely unanticipated exception (a bug in
  the Worker's *own* error-handling path, e.g. its failure-report write
  itself hitting a full disk) could previously propagate out of
  `Worker.process()` entirely and end the whole batch. A last-resort
  boundary in `ProcessingService._run_one_job()` now guarantees no
  single article can ever stop the run — matches this milestone's
  top-line goal directly.
- **[VERIFIED, NO ACTION]** Operator_Checklist/Batch_Audit_Report bucket
  mapping matches the real code exactly; batch history layout, manual
  review flow, and download routes all confirmed correct against real
  batch output.

## 13. Documentation

Updated only where a real code change made the existing docs
inaccurate: `Operator_Guide.md` (new Certification Report section,
corrected Dashboard behavior, restart-subset/mid-run-freshness notes),
`01_BUSINESS_RULE_BOOK.md` (2 clerical corrections, no rule content
changed). No new documentation beyond the 4 requested deliverables.
