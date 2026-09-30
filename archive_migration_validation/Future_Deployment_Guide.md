# Future Deployment Guide

## Phase 3 (Dashboard)

Nothing in the engine needs to change. `ProcessingService.run()` returns
a `BatchStatusSnapshot` (`service/status.py`) carrying, per package:
status, warnings, recoveries, tracked Business Rule failures, confidence
score/level, generated files, download location, retry count, and
duration — plus a `ProgressSnapshot` (total/completed/remaining/
percentage/ETA). A dashboard reads these directly; it does not need to
re-derive anything from `ConversionReport` itself.

Not yet done: persisting `BatchStatusSnapshot` anywhere a dashboard
process could read it live (today it's an in-memory return value of one
`run()` call). A real dashboard needs either a lightweight persistence
layer for it, or the dashboard to run in-process alongside the service.

## Phase 4 (Cloud Integration)

- `S3InputProvider`/`SftpOutputProvider` (`providers/input.py`,
  `providers/output.py`) are placeholders — implement their bodies, add
  connection settings to `InputSettings`/`OutputSettings` +
  their JSON Schemas, and switch `runtime.yaml`'s `provider` values. No
  `service/` code changes.
- `meca_engine.retry`'s classification already anticipates this:
  `S3ReadTransientError`/`S3WriteTransientError` are already
  `retryable = True` `ArticleTransientError` subclasses — an S3 provider
  raising them gets retry behavior for free, no `retry/` changes needed.
- **Durable checkpoint backend.** Today's `InMemoryCheckpointStore` does
  not survive a process restart (see `Service_Verification.md`'s "Known
  limitation"). Real crash-resume across restarts needs a durable
  `CheckpointStore` implementation (Postgres/DynamoDB, per the store's
  own docstring, TQ-03) — a new class implementing the existing
  `CheckpointStore` ABC, no changes to `PackageBatchRunner` or `Worker`.
- **Concurrency.** `Worker`/`ProcessingService` process one job at a
  time by design (this phase's explicit scope). `PackageBatchRunner`'s
  checkpoint claim/skip logic is already safe under concurrent access
  (tested: 5 concurrent threads on the same article process it exactly
  once) — a future parallel dispatcher can drive multiple `Worker`
  instances against the same shared `CheckpointStore` without changing
  either class.
- A real queue broker (SQS/RabbitMQ) would replace `JobQueue` behind the
  same `enqueue`/`dequeue`/`size`/`empty` shape `ProcessingService` uses
  today — nothing else in the call chain needs to know.
