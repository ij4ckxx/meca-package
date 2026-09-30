# Service Implementation Summary

## What was implemented

A new `src/meca_engine/service/` package replaces the batch script's inline
orchestration with a reusable Processing Service: `Job` → `JobQueue` →
`Worker` → (existing extraction/transformation/`PackageBatchRunner`/
`PackageBuilder` pipeline, unchanged) → `ConversionReport` → reporting/
certification/intelligence (existing, unchanged) → `OutputProvider`.
`scripts/archive_migration_batch.py` is now 30 lines: load config, build
the service, run it.

Also added: `meca_engine/retry/` (previously an empty, reserved LLD stub)
now implements transient-failure classification + exponential backoff,
used by the Worker for operational resilience — the one genuinely new
piece of logic this phase adds; everything else is existing code, reused.

## Files created

- `src/meca_engine/service/__init__.py`, `job.py`, `queue.py`, `worker.py`,
  `progress.py`, `status.py`, `processing_service.py`, `service_factory.py`
- `src/meca_engine/retry/__init__.py` (filled in, was an empty stub)
- `tests/unit/service/` (job, queue, progress, status, worker)
- `tests/unit/retry/test_retry.py`

## Files modified

- `src/meca_engine/packaging/batch_runner.py` — added one optional field,
  `PackageOutcome.exception: MecaEngineError | None`, purely additive, so
  a caller can recover the real exception (not just its string form) for
  report classification and retry decisions. Zero behavior change;
  existing tests pass unmodified, one new assertion added.
- `scripts/archive_migration_batch.py` — reduced to a bootstrap.

## Architecture decisions

**Reused, not rebuilt:** `CheckpointStore`/`InMemoryCheckpointStore`/
`ArticleStage` (via `PackageBatchRunner`, unmodified), `PackageBatchRunner`
itself, every extraction/transformation/generation/packaging/reporting/
certification/intelligence module, `ConfigLoader`/`RuntimeConfig`, and the
Provider framework from Phase 1. Nothing in this list was changed.

**`orchestrator/`, `input/readers/`, and the old discovery pipeline were
left untouched**, as instructed — they're superseded (coupled to an input
layer Phase 1 already replaced) and out of scope for an orchestration-only
phase.

**Retry logic lives in `meca_engine/retry/`, not in `service/`.** This
reserved package's own docstring already claimed
(`ArticleTransientError`'s docs) that `meca_engine.retry` "automatically
retries subclasses of this error" — it was just never implemented. Filling
it in here makes that claim true and gives the engine a real, reusable
retry facility instead of one buried inside the service layer.
`service/worker.py` only calls into it.

**Retry classification reuses the exception hierarchy's own signal**:
`MecaEngineError.retryable` (already `True` on `ArticleTransientError` and
its subclasses — `S3ReadTransientError`, `DoiRegistryUnavailableError`,
`CheckpointStoreUnavailableError`, etc. — and `False` by default on every
data-quality exception), plus a conservative stdlib fallback (`OSError`/
`ConnectionError`/`TimeoutError`, excluding `FileNotFoundError` and other
deterministic `OSError` subtypes) for raw exceptions not yet wrapped. No
new classification scheme was invented.

**`PackageBatchRunner`/`PackageBuilder` were not modified in the way they
build packages** — the only change is the one additive `PackageOutcome`
field above, needed because `PackageBatchRunner` swallows a failure's
exception into a string, which would otherwise break both retry
classification and `_classify_failure`'s exception-type check.

## Engine behavior

Unchanged and verified: a full 37-package run through the new service
produced the same shape of outcome (37/37 packages generated, 0 engine
failures, 0 fatal failures) as before this refactor. See
`Service_Verification.md`.
