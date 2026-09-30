# Service Configuration Guide

No new configuration model. The service reuses `RuntimeConfig`/
`ConfigLoader`/`runtime.yaml`/the existing JSON Schema exactly as Phase 1
left them — no new settings were added for this phase.

## What the service reads

- `input.provider` / `input.local_path` — via `InputProvider` (Phase 1)
- `output.provider` / `output.local_path` — via `OutputProvider` (Phase 1)
- `dashboard.reports_path` — where corpus-level reports are written
- `retry.max_attempts` / `retry.backoff_base_seconds` /
  `retry.backoff_multiplier` / `retry.backoff_max_seconds` — **newly
  consumed** by `Worker` via `meca_engine.retry.run_with_retry`. This
  section already existed in `runtime.yaml` (added in an earlier
  milestone) but was previously unused by any code; the service is its
  first real consumer.

No other section changed meaning.

## Local-as-S3, Local-as-SFTP

`input.provider: LOCAL` / `output.provider: LOCAL` behave exactly as
"S3" and "SFTP" will once implemented: the Worker only calls the
`InputProvider`/`OutputProvider` interface, never a concrete class.
Switching to `S3`/`SFTP` once those providers have real implementations
requires only a `runtime.yaml` change — no code in `service/` changes.

## Adding S3/SFTP later

Same as documented in the Phase 1 Configuration Guide
(`12_Phase1_Configuration_Guide.md`): implement `S3InputProvider`/
`SftpOutputProvider`'s bodies (currently placeholders raising
`ProviderNotConfiguredError`), add whatever connection settings they need
to `InputSettings`/`OutputSettings`, and flip the `provider` value.
Nothing in `service/` needs to change.
