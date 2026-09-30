# Known Limitations

- **DOI search is not implemented.** `ConversionReport` (Reporting)
  doesn't carry a DOI field today; adding one would mean modifying
  Reporting, which is out of scope for a wiring-only phase. Search
  covers article id, journal, status, recovery rule, business rule, and
  warning code.
- **Config edits lose YAML comments.** Saving through the dashboard
  rewrites the whole `runtime.yaml` via `yaml.safe_dump`, so
  hand-written comments don't survive a dashboard-made edit. Editing the
  file directly is unaffected.
- **Cancel is a hard kill, not a graceful stop.** It sends SIGTERM
  immediately rather than waiting for the current article. This is
  intentional (matches "Cancel" being more abrupt than "Stop After
  Current Article") and safe — the existing checkpoint framework redoes
  any interrupted article from scratch on the next run — but a cancelled
  batch's `live_status.json` may briefly lag before the dashboard
  reports it correctly (handled: the controller overrides the reported
  state once it knows a cancel was issued).
- **Batch History has no automatic cleanup.** Every run creates a new
  `batches/<id>/` directory forever; nothing prunes old ones. Delete old
  batch folders manually if disk space matters.
- **The dashboard doesn't survive its own restart mid-run gracefully.**
  If you stop `npm run dev` while a migration is running, that Python
  process keeps running orphaned (see Deployment Guide) — the dashboard
  has no "reattach to an already-running batch on startup" logic.
- **`restart-failed` was verified by code-path symmetry, not live**,
  since the current real corpus has zero failed articles to test
  against. It uses the exact same `runController.start(articleIds)` path
  already verified live for `restart-manual-review`, with the article
  ids sourced from `failed/` instead of `manual_review/`.
- **Search/filter and analytics are read-time computations over
  already-generated JSON**, not live database queries — fine at this
  corpus size (tens of articles); would need real indexing at a much
  larger scale, which is out of scope here.
- **No authentication.** The dashboard has no login — appropriate for a
  local, single-operator tool; would need adding before any shared or
  network-exposed deployment.
