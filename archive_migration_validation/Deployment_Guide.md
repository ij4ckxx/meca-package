# Deployment Guide (Local Production Mode)

## One-time setup

```bash
cd dashboard
npm run install:all
```

Requires a `python3` on PATH with the engine's dependencies installed
(same requirement as running `scripts/archive_migration_batch.py` by
hand — nothing new). If your environment needs a specific interpreter or
`PYTHONPATH`, set `DASHBOARD_PYTHON_BIN`/`DASHBOARD_PYTHONPATH_EXTRA`
(see `Configuration_Guide.md`).

## Start everything with one command

```bash
cd dashboard
npm run dev
```

Starts the Dashboard API (port 4000) and the Dashboard UI (port 5173)
together. Open `http://localhost:5173`. Ctrl-C stops both.

If a migration is running when you stop the dashboard, the Python
process is orphaned (not killed) — reopen the dashboard and it can be
cancelled/inspected once you find its batch id under
`archive_migration_validation/batches/`, or just let it finish; it
writes its results normally either way.

## Ports

Both ports are configurable if already in use on your machine:

```bash
PORT=4001 npm run dev --prefix server   # dashboard API
# and separately:
npm run dev --prefix web -- --port 5174 # dashboard UI (update vite.config.ts's proxy target to match if you change the API port)
```

## Output folders

Nothing to create manually — `archive_migration_validation/batches/<id>/`
and its subfolders are created on demand by the first migration run.

## Cloud readiness (not implemented, by design)

`S3InputProvider`/`SftpOutputProvider` remain placeholders. Enabling
them later is a `runtime.yaml` change only (`input.provider: S3` /
`output.provider: SFTP` plus whatever connection settings their
eventual implementations need) — no dashboard or `service/` code
changes required.
