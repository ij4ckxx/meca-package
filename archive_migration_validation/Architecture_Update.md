# Architecture Update

## New flow

```
Input Location
      │
      ▼
Dashboard "Start Migration" ──spawns──► python3 scripts/archive_migration_batch.py --batch-id <id>
      │                                          │
      │                                          ▼
      │                                 ProcessingService.run()
      │                                   ├─ checks batches/<id>/control.json between articles
      │                                   ├─ writes batches/<id>/live_status.json after each article
      │                                   └─ MECA Engine → Conversion Report → Output Router
      │                                          │              ├──► batches/<id>/generated_packages/uploaded/
      │                                          │              ├──► .../manual_review/
      │                                          │              └──► .../failed/
      │                                          ▼
      │                                 batches/<id>/reports/*  (unchanged reporting/intelligence)
      ▼
Dashboard API polls control.json / live_status.json / the output folders
      │
      ▼
Dashboard UI (polls the API every few seconds — no websockets)
```

## New components

| Component | Location | Role |
|---|---|---|
| `service/control.py` | Python | Pause/stop/cancel file-based signaling; live-status writer |
| `--batch-id`/`--article-ids` | `scripts/archive_migration_batch.py` | Batch History nesting; restart-subset |
| `scripts/update_runtime_config.py` | Python | Validated config write-back, reusing `ConfigLoader` |
| `runController.ts` | Dashboard server | Spawns/controls the Python process, captures logs |
| `batchStore.ts` | Dashboard server | Lists/resolves batches for Batch History |
| `configStore.ts` | Dashboard server | Reads `runtime.yaml`; delegates writes to the Python script |
| `dataStore.ts` (updated) | Dashboard server | Now batch-parameterized instead of one fixed path |
| Control Center, Logs, Configuration pages | Dashboard web | New UI surfaces |
| Batch selector, search/filters | Dashboard web | Threaded through every existing page |

## What did not change

`PackageBuilder`, all 5 generators, Business Rules, Recovery Rules,
Certification, Reporting calculations, Intelligence calculations, XML
handling, and the config schema itself. The dashboard and the new
control/batch-history code only consume these — they never compute
anything Reporting/Intelligence already compute.

## Process boundary

The dashboard and the engine remain **two separate processes**,
communicating only through the filesystem: a JSON control file, a JSON
status file, and the same output/report directories every prior phase
already produced. No new RPC framework, no websockets — matches the
spec's explicit "polling is fine" guidance and keeps the engine
completely unaware that a dashboard exists.
