# Verification Summary — RC-1 Milestone

Lightweight, as instructed — targeted tests for changed code, one full
regression run, one full batch run.

## Targeted tests for changed code

- `meca-engine/tests/unit/providers/test_input.py` — added
  `test_local_input_provider_rejects_a_zip_slip_member`; all 11 tests
  pass.
- `meca-engine/tests/unit/config/` — re-ran after annotating
  `runtime.yaml`; all 55 pass (comments don't affect YAML/schema
  validation).
- Dashboard server has no existing test framework (no `.test.ts` files,
  no jest/vitest configured) — the 2 changes there (`resolveBatchId`
  validation, `loadConversionReports` caching) were verified live
  against the running dev server instead: confirmed the traversal
  payload now 404s, a real batch id still returns full correct data,
  and both `tsc -p tsconfig.json --noEmit` (server) / `tsc -b --noEmit`
  (web) are clean.

## One full regression run

`pytest tests/` (meca-engine): **1163 passed, 3 failed** — the same 3
pre-existing, unrelated golden ICAM snapshot failures documented in
every prior milestone's summary this session (affiliation
`country`/`institution` fields; no code path this milestone touches).
`ruff check`, `ruff format --check`, `mypy --strict` clean on every
modified file.

## One full batch run

`Input/` (97 articles), verified after all RC-1 changes:

```
Total: 97
  certified_with_warnings: 14
  certified_with_recovery: 71
  partial_certification: 10
  engine_failure: 0
  fatal_failure: 2

Packages generated: 95/97
Total recoveries: 442
```

**Identical to the prior (Quality Improvement) milestone's final run** —
confirms zero package-generation regression from repository cleanup,
config annotation, the zip-slip guard, the batch-id validation fix, the
Dashboard caching change, or the version bump.

## One correction made mid-milestone, disclosed

Initial repository cleanup archived `Output/` (moved to `_archive/`)
believing it was an unused historical artifact — the full regression run
caught that 5 golden tests read from it directly, restored it
immediately, and re-ran the full suite to confirm (back to 1163
passed / 3 pre-existing failures). All comment edits that had pointed at
the archived location were reverted to match. This is exactly why the
milestone's own "run a full regression pass" verification step exists,
and it did its job.
