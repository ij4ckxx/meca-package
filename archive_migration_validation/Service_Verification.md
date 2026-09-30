# Service Verification

- Full suite: 1097 passed, 3 pre-existing failures — ✅ (see note below)
- `ruff check` / `ruff format --check` — clean on every file this phase touched — ✅
- `mypy --strict src/` — 151 files, 0 issues — ✅
- Targeted new tests: `tests/unit/retry/` (10), `tests/unit/service/` (14), plus 1 new assertion in `tests/unit/packaging/test_batch_runner.py` — all passing — ✅
- One real package via the new `ProcessingService` — ✅ (`bcj-2025-3130`, `certified_with_recovery`)
- One small batch (4 real packages) — ✅ (4/4 succeeded, `certified_with_recovery`)
- One larger batch, the current `Input/` folder (37 real packages) — ✅ (37/37 generated, 0 engine failures, 0 fatal failures — same outcome shape as before this refactor)
- `./Output/` (3 protected reference packages) — untouched throughout (MD5-verified before/after) — ✅
- `scripts/archive_migration_batch.py` reduced to config-load + service-build + run, no orchestration logic left in it — ✅

## Pre-existing failure (not caused by this work)

`tests/golden/test_metadata_to_icam_golden.py` has 3 failures
(`CS-2025-6808`, `CS-2025-8493_C`, `cs-2025-8827`) comparing affiliation
extraction against a golden snapshot. Confirmed unrelated: the test only
imports `extraction`/`model`/`transform`/`logging_` modules, none of which
this phase touched, and none of those files' mtimes are from this session.
Left as-is — fixing it would mean touching ICAM/extraction logic, out of
this orchestration-only phase's scope.

## Known limitation: cross-process resume

`Worker` retries transient failures *within* one process run (verified:
a simulated transient failure at staging was retried once, then
succeeded). Checkpoint state does **not** persist across separate
invocations of `scripts/archive_migration_batch.py` — `InMemoryCheckpointStore`
is constructed fresh each run, by design (it's the existing, in-memory-only
backend; a durable backend is explicitly deferred in its own docstring).
Verified empirically: running the small 4-package batch twice in a row
reprocessed all 4 articles both times, none skipped. "Restart unfinished
packages after a crash" therefore works today only in the sense that
reprocessing is safe and idempotent (checkpoint claims collide correctly
against concurrent access), not in the sense of skipping already-finished
work across a restart — that requires a durable `CheckpointStore` backend,
which is future work (see `Future_Deployment_Guide.md`).

## Not run, per scope

Full historical certification programme, full historical report
regeneration, all previous milestone validation.
