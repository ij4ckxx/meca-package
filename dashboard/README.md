# MECA Migration Dashboard

An operator dashboard for the Archive Migration Platform: view every
article, control live migration runs, browse batch history, and edit
runtime configuration. Never runs conversion logic itself — it spawns
the same `scripts/archive_migration_batch.py` an operator would run by
hand, and reads its output.

## Stack

- `server/` — Node/Express + TypeScript API. Spawns/controls the Python
  batch process, reads its JSON reports, scans the
  `uploaded/`/`manual_review/`/`failed/` output folders per batch.
- `web/` — React + TypeScript (Vite) frontend.

## Running locally (one command)

```bash
cd dashboard
npm run install:all   # once
npm run dev           # starts both API (4000) and UI (5173)
```

Open `http://localhost:5173`.

Requires a `python3` on PATH with the engine's dependencies already
installed (same requirement as running the batch script directly). If
your environment needs a specific interpreter, set
`DASHBOARD_PYTHON_BIN`/`DASHBOARD_PYTHONPATH_EXTRA` before running
`npm run dev` — see `Configuration_Guide.md` in
`archive_migration_validation/`.

## Batch History

Every "Start Migration" creates a new batch under
`archive_migration_validation/batches/<batch-id>/`. The sidebar's batch
selector switches every page between "Latest" and any prior batch.

## Pages

- **Control Center** (home) — Start/Pause/Resume/Stop After Current/
  Cancel, Restart Failed/Manual-Review Articles, and live job status
  (current article, remaining, elapsed, ETA, speed) polled every ~3s.
- **Home** — corpus-wide counts for the selected batch.
- **Per Journal** — article count, recovery rate, common recovery rule,
  warnings, average confidence.
- **Articles** — search (article id, journal, status, recovery/business
  rule, warning code) + filters (journal, status, confidence).
- **Article detail** — status/confidence/warnings/recoveries, 6 tabs,
  and 3 downloads (MECA ZIP, Certification Report, conversion-report.json).
- **Manual Review** — articles routed to `manual_review/`, with reason,
  download, and a "restart all" action.
- **Analytics** — success %/manual-review %, confidence distribution,
  Recovery Rule Effectiveness, Warning Analytics — all read from the
  engine's own intelligence output.
- **Logs** — live tail of the current/most recent run's console output.
- **Configuration** — edit and save `runtime.yaml`, validated against
  the engine's own schema.

## API

See `archive_migration_validation/Architecture_Update.md` for the full
endpoint list and control-flow diagram.

## Not built (by design)

An "Upload to SFTP" button — no real SFTP provider exists yet. Add it
once `SftpOutputProvider` is implemented; nothing else changes.
