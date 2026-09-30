# Production Verification — Final Production Readiness Milestone

Lightweight, as instructed — targeted unit tests for modified code, one
complete batch run, no repeated benchmark passes.

## Targeted unit tests (new/changed behavior only)

New or extended regression tests, one per confirmed fix:

- `tests/unit/service/test_worker.py` — case-insensitive journal lookup
  (prior milestone); `_classify_failure` parametrized across every
  relevant exception type, including `ArticleTransientError` now →
  `ENGINE_FAILURE`.
- `tests/unit/providers/test_input.py` — missing/corrupt/empty archive
  exception types (prior milestone); temp-extraction-directory removed
  on a staging failure.
- `tests/unit/packaging/test_builder.py` — a raw `OSError` from the zip
  builder is now reported as `PackageAssemblyError`, not left
  unclassified.
- `tests/unit/validation/test_package_validator.py` (new file) — never
  raises when the already-built zip is missing or corrupt.
- `tests/unit/extraction/test_file_resolver.py` — the free-text-label
  substitution risk no longer resolves to an unrelated file; a
  genuinely short, real declared name still resolves correctly via the
  prefix tier.
- `tests/unit/validation/test_dtd_issue_classifier.py` — `con<N>`
  duplicate ids now classify as `source_data_issue`, same as `aff`/`cor`.
- `tests/unit/reporting/test_certification_report.py` (new file) — a
  failed article's report now shows its real failure reason; a
  successful article shows no such section.
- `tests/unit/service/test_processing_service.py` — `conversion_reports.json`
  refreshes mid-run (not only at the end); restarting a narrower subset
  under the same batch-id preserves every prior article's record; one
  article's exception inside the Worker's own error handling never stops
  the batch.

**Result**: 1161 passed. Full suite (`pytest tests/`): same 3
pre-existing, unrelated golden-snapshot failures documented in every
prior milestone's summary (affiliation `country`/`institution` fields —
no code path this milestone touches). `ruff check`, `ruff format --check`,
and `mypy --strict` all clean on every modified Python file.
`tsc -p tsconfig.json --noEmit` (dashboard server) and `tsc -b --noEmit`
(dashboard web) both clean.

## One complete batch run

`Input/` (97 articles — the full current corpus), batch id
`production-readiness-final`:

```
Total: 97
  certified: 0
  certified_with_warnings: 14
  certified_with_recovery: 72
  partial_certification: 9
  engine_failure: 0
  fatal_failure: 2

Packages generated: 95/97
Total recoveries: 442
```

**Identical to the prior milestone's final verification run** —
confirms this milestone's fixes changed no package-generation behavior
for any article that was already succeeding; both remaining failures
(`ebc-2025-3025` empty zip, `ebc-2025-3021_C` missing manuscript) are
correctly `fatal_failure`, and `engine_failure` remains 0 across the
whole corpus.

## Fixes spot-checked directly against this run's real output

- `CS-2025-6808`/`bcj-2025-3298`'s `ID con<N> already defined` DTD
  findings now classify as `source_data_issue` (confirmed via
  `conversion_reports.json`), not the `validation_only` default.
- `CS-2025-6808`'s `"1.manuscript highlight yellow 1"` file entry still
  resolves to its correct real physical file (via the safer "stem"
  tier) — confirming the RR-004 prefix-tier fix changed no real match in
  the current corpus while closing the latent substitution risk.
- Manually reproduced the "restart a subset under the same batch-id"
  scenario end-to-end via the real CLI (3-article batch, then a
  1-article restart under the same batch-id): before the fix,
  `conversion_reports.json` dropped to 1 article; after the fix, all 4
  are present.

## Deviations from requested scope

None. Every item marked `[RECOMMEND]` in `Production_Findings.md` was
deliberately left unimplemented per its own stated reasoning (a genuine
product decision, a zero-real-world-impact dormant code path, or a
change whose regression risk exceeded this milestone's "minimal
changes" bar) — never silently skipped.
