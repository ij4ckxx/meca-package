# Operational Guide

## Running the service

```
python3 scripts/archive_migration_batch.py
```
Loads `config/runtime.yaml` via `ConfigLoader`, builds the Processing
Service, runs every article the configured `InputProvider` reports.

## Where things end up

Under `output.local_path` (default
`archive_migration_validation/generated_packages/`):

- **`uploaded/<article_id>/`** — certified packages (clean, with
  warnings, or with recovery). Nothing further to do; treat as done.
- **`manual_review/<article_id>/`** — partially certified packages.
  Contains the MECA zip, Certification Report, and
  `conversion-report.json` — everything a reviewer needs to decide
  whether to release it manually.
- **`failed/<article_id>/`** — engine or fatal failures. No package
  exists (none could be built); contains the Certification Report and
  `conversion-report.json` describing what went wrong, for investigation.

Corpus-level reports (Migration Summary, audit CSVs, analytics,
intelligence reports, dashboard JSON) are at `dashboard.reports_path`
(default `archive_migration_validation/`), unchanged from before this
phase.

## Reading the console output

Each article prints its status and elapsed time as it completes; a final
`=== SUMMARY ===` block gives the per-status counts and totals. Nothing
in `uploaded/manual_review/failed` is ever silently dropped — every
processed article is counted in the summary and lands in exactly one
folder.

## Re-running

Safe to re-run: `output.local_path`'s category folders accumulate one
subfolder per article. Checkpoint-based skip protects against
duplicate-dispatch *within* one run; it does not persist across separate
process invocations (see Phase 2's `Service_Verification.md` — the
reused `CheckpointStore` is in-memory only by design), so a full re-run
reprocesses every article again — safe and idempotent, just not
"resume from where it stopped" across restarts. Durable cross-restart
resume is future work (Phase 4).

## Switching providers

Change `input.provider`/`output.provider` in `runtime.yaml`
(`LOCAL`/`S3`/`SFTP`) — no code changes anywhere in `service/`. `S3`/
`SFTP` are currently placeholders (raise `ProviderNotConfiguredError`
until implemented).
