# Configuration Guide

## Editing via the Dashboard

Configuration page → edit → Save. Every save is validated against the
engine's existing JSON Schema (`schemas/config-schema/runtime.schema.json`)
before being written; an invalid value is rejected and `runtime.yaml` is
left unchanged, with the schema's own error message shown.

Fields exposed: Input Provider (`input.provider`/`input.local_path`),
Output Provider (`output.provider`/`output.local_path`), Dashboard
folders (`dashboard.reports_path`), Worker Count
(`concurrency.worker_count`), Retry settings (all 4
`retry.*` fields), Logging level (`logging.level`), and Processing
options (`packaging.overwrite_policy`, `validation.severity_block_threshold`).

## Known limitation

Saving through the dashboard rewrites the whole `runtime.yaml` file, so
hand-written comments in it are not preserved across a dashboard edit
(round-trip-preserving YAML would need a new dependency — not worth it
for this). Editing the file directly still works exactly as before and
keeps its comments.

## Environment variables (dashboard server only, not engine config)

- `DASHBOARD_PYTHON_BIN` — the `python3` binary to spawn (default:
  `python3` on PATH). Set this if your machine's default `python3`
  doesn't already have the engine's dependencies installed.
- `DASHBOARD_PYTHONPATH_EXTRA` — prepended to `PYTHONPATH` before
  spawning, for environments where dependencies live somewhere
  non-standard.
- `DASHBOARD_DATA_ROOT` — override for
  `archive_migration_validation/` if it's not at the default relative
  location.
- `PORT` (server) / dev server `--port` (web) — see Deployment Guide.

## What did not change

`RuntimeConfig`, `ConfigLoader`, and every JSON Schema — untouched. The
dashboard only reads/writes the same `runtime.yaml` the engine has
always used.
