# Security Review — RC-1

Lightweight, targeted review per the milestone's own scope — real issues
fixed, no architectural changes.

## Fixed: path traversal / directory escape in the Dashboard API

**`dashboard/server/src/batchStore.ts`, `resolveBatchId()`.** Every
dashboard API route resolves its batch via
`requireBatch(req) → resolveBatchId(req.query.batch)`, and that value
was returned **completely unvalidated** — `req.query.batch` flows
straight from a URL query parameter into `batchDataRoot()`/
`batchPackagesRoot()`, which `path.join()` directly onto `BATCHES_ROOT`
with no sanitization. A request like
`GET /api/articles?batch=../../../../etc` would resolve outside the
intended `batches/` directory entirely, and downstream code
(`readFileSync`, `res.sendFile`, `readdirSync`) would then read/serve
whatever that resolved path pointed at — a real, confirmed
directory-escape vulnerability, not theoretical.

**Fixed**: `resolveBatchId()` now only ever returns a value that matches
a real, existing batch directory name (validated against `listBatches()`,
the same enumeration the `/api/batches` endpoint already uses); anything
else returns `null`, which every route already handles as a 404 ("No
migration has run yet"). **Verified live** against the running dev
server (which hot-reloads): the traversal payload now returns the
generic 404, and a real batch id (`?batch=2026-09-20T08-08-44-653Z`)
still returns full, correct data — confirmed no regression.

## Fixed: zip-slip in archive extraction

**`meca-engine/src/meca_engine/providers/input.py`,
`LocalInputProvider.stage_article()`.** Every article's source `.zip`
is extracted via `zipfile.ZipFile.extractall()`, whose stdlib
implementation does **not** sanitize member paths (Python's own docs
warn: extracting from an untrusted zip can create files outside the
target directory). A member named e.g. `"../../../etc/cron.d/evil"` or
an absolute path would not have been rejected before extraction.

**Fixed**: added `_reject_unsafe_members()`, called before
`extractall()`, which resolves every member's intended path and rejects
the *whole archive* (raising `InvalidArticlePackageError`, a source-data
classification, not an engine failure) if any single member would
escape the staging directory — a crafted path is treated as a sign the
archive itself shouldn't be trusted, not something to silently skip.
**Verified** with a new regression test
(`test_local_input_provider_rejects_a_zip_slip_member`) reproducing the
exact attack shape; all 11 tests in `test_input.py` pass.

## Reviewed, confirmed safe (no change needed)

- **HTML rendering**: all 6 HTML report generators
  (`reporting/{certification_report,migration_audit,validation_report,batch_audit_report,operator_checklist,transformation_summary}.py`)
  consistently use `html.escape()` on every interpolated value — spot-
  checked counts (8-25 escape calls per file, none zero).
- **Dashboard file-serving routes**: `resolveReportFile()` checks a
  strict exact-match allowlist (`REPORT_FILE_ALLOWLIST`) before ever
  constructing a path — a traversal payload simply won't match any
  allowlisted filename. `getArticleFile()`/`getArticleXml()` look up the
  requested article id in a `Map` built entirely from a prior
  `readdirSync()` enumeration of real directories — a fabricated id
  can't be a key in that map, so it 404s rather than resolving anywhere.
- **Command injection**: both dashboard-triggered subprocess calls
  (`runController.ts`'s batch-start, `configStore.ts`'s config update)
  use `child_process.spawn()` with an **argument array**, never a shell
  string — user-supplied values (article ids, config JSON) are passed as
  literal argv/stdin data, never interpreted by a shell.
- **Config-injection via `PUT /api/config`**: delegates to
  `scripts/update_runtime_config.py`, which uses `yaml.safe_load`/
  `yaml.safe_dump` (never the unsafe YAML loader), validates the merged
  result against the existing JSON Schema before committing, and rolls
  back the file to its original content on validation failure. No
  arbitrary-object-deserialization or schema-bypass risk found.
- **Temp file leaks**: covered in the prior Production Readiness
  milestone (extraction temp directories are now cleaned up on every
  outcome, success or failure) — re-confirmed still in place, unrelated
  to this milestone's changes.

## Known, pre-existing, explicitly out-of-scope gap

The Dashboard API has **no authentication** at all today — every route,
including `PUT /api/config` (writes runtime configuration) and the
`/run/*` batch-control endpoints, is open to anyone who can reach the
server. This is a real exposure if the dashboard is ever run on a
network reachable by untrusted parties, but implementing authentication
is explicitly excluded from this milestone's scope ("No Authentication.
No User Management."). Flagged here for visibility ahead of any
network-exposed deployment, not fixed.
