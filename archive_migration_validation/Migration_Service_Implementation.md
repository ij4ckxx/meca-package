# Migration Service Implementation

## What was implemented

Decision-based output routing added to the existing Processing Service:
after each article's `ConversionReport` is built (Certification/Reporting
already run, unchanged), a new `OutputRouter` moves the finished package
(or, for a failure, writes just its Certification Report + a
`conversion-report.json`) into one of three `OutputProvider`-managed
folders, per a fixed decision matrix. Nothing about extraction,
transformation, generation, `PackageBuilder`, certification, reporting,
or intelligence changed — only where each article's artifacts end up.

## Decision matrix (mapped to the real `PackageStatus` enum)

| Report status | Category |
|---|---|
| `CERTIFIED`, `CERTIFIED_WITH_WARNINGS`, `CERTIFIED_WITH_RECOVERY` | `uploaded` (automatic) |
| `PARTIAL_CERTIFICATION` | `manual_review` |
| `ENGINE_FAILURE`, `FATAL_FAILURE` | `failed` |

(The prompt's `CERTIFIED_WITH_WARNING`/`FAILED_ENGINE`/`FAILED_FATAL`
names don't exist in the engine — mapped to the real
`CERTIFIED_WITH_WARNINGS`/`ENGINE_FAILURE`/`FATAL_FAILURE` values.)

No package is ever discarded — every article lands in exactly one folder.

## Files created

- `src/meca_engine/service/router.py` — `decide_category()`, `OutputRouter`
  (`route_built_package()` moves a finished package to its category;
  `route_failed_article()` writes a failed article's Certification Report
  + `conversion-report.json`, reusing the existing writer and
  `ConversionReport.to_dict()` — no new report format).
- `tests/unit/service/test_router.py`

## Files modified

- `src/meca_engine/providers/output.py` — `OutputProvider` gained one new
  abstract method, `category_root(category) -> Path`, implemented in
  `LocalOutputProvider` (creates `<local_path>/<category>/`) and
  `SftpOutputProvider` (placeholder, same as `article_output_root`).
  Additive: `article_output_root`'s existing behavior is unchanged.
- `src/meca_engine/service/worker.py` — after a package is built, calls
  `OutputRouter.route_built_package()` instead of leaving it at the
  neutral staging root; on failure, calls `route_failed_article()`
  instead of the old `_write_fallback_certification_report` (removed —
  superseded by the new `failed/` category, which is what the prompt's
  Output Structure asked for). `job.output_location` now reflects the
  real final location.
- `src/meca_engine/service/service_factory.py` — constructs one
  `OutputRouter` per batch, injected into `Worker`.
- `tests/unit/providers/test_output.py`, `tests/unit/service/test_worker.py`
  — updated for the new interface/constructor signature.

## Reused, unchanged

`ProcessingService`, `JobQueue`, `PackageBatchRunner`, the Checkpoint
framework, `InputProvider`/`OutputProvider`'s existing methods, the retry
framework, `PackageBuilder`, all reporting and intelligence modules. The
corpus-level `reports/` location stays exactly as Phase 1/2 left it
(`dashboard.reports_path`, not re-routed through `OutputProvider`) — a
deliberate choice to avoid re-wiring already-verified reporting plumbing
for a phase that only asked for orchestration.

## Configuration

No new configuration. `RuntimeConfig`/`OutputSettings`/`ConfigLoader` are
unchanged — the category folders are subdirectories of the existing
`output.local_path`, not new config keys.
