# Dashboard Verification

- `tsc -b --noEmit` (web) / `tsc --noEmit` (server) — both clean — ✅
- Production builds: `vite build` and `tsc -p tsconfig.json` — both
  succeed — ✅ (Vite flags one large chunk, from `jspdf`/`html2canvas`
  for PDF export; a non-blocking bundle-size note, not a correctness
  issue)
- `npm audit` — 0 vulnerabilities on both `server` and `web` (after
  rejecting `xlsx`/`exceljs` for unpatched CVEs — see Enhancement
  Summary) — ✅
- Dashboard starts locally with one command (`npm run dev` from
  `dashboard/`) — ✅
- Existing 37-article dataset loads correctly — verified via
  `/api/summary`, `/api/journals`, `/api/articles`, `/api/manual-review`
  against the real batch from Phase 5 — counts match exactly (37 total,
  33 uploaded, 4 manual review, 0 failed) — ✅
- A second real batch was run live through the dashboard
  (restart-manual-review, 4 articles) specifically to verify Batch
  History and Batch Comparison against real data (not mocked) — ✅
- Batch History — enriched stats (success/recovery/manual-review/failed/duration)
  verified correct for both real batches — ✅
- Batch Comparison — verified the underlying data both batches load
  correctly and genuinely differ (batch A: 30 certified-with-recovery / 4
  partial / 3 certified-with-warnings; batch B: 4 partial only) — ✅
- Downloads verified directly against real files: MECA ZIP, all 5 XML
  documents individually (extracted from the real zip), Certification
  Report, `conversion-report.json`, and 2 named report files
  (Migration Summary, Journal Health Report) — ✅
- Search verified: found the correct 32/37 articles for a known
  recovery code in the full batch, and the correct 3/4 in the restart
  batch — matching the corpus's own known numbers exactly — ✅
- Filters verified: journal, status, confidence, warning-code — ✅
- Manual review notes verified: set a note + status on one article,
  confirmed it persisted and is correctly isolated per batch (the
  second batch's notes started fresh, not inheriting the first batch's) — ✅
- Package size, business-rule analytics, and top-missing-files
  endpoints verified against real data — ✅

## Two real bugs found and fixed during this verification

The warning filter and global search on `/api/articles` only checked
`ConversionReport.warnings`, which is empty for every article in this
corpus — everything here is classified as a `recovery` instead. Both
were fixed to check `warnings` and `recoveries` together, matching how
the engine's own intelligence layer already treats them for its Warning
Analytics table. The same issue was caught and fixed in the new
per-journal "most common warning" field before it ever shipped.

## Not run, per scope

Full Python regression suite — no Python code was changed this phase.
Package regeneration / re-running the engine beyond the 2 real batches
above (used specifically to prove Batch History/Comparison against real
data, not synthetic).

## Not visually verified

No browser/screenshot tool is available in this environment. Every
claim above is backed by direct API verification against real data,
clean builds, and clean typechecks — not a rendered visual check. Please
open `http://localhost:5173` yourself to confirm layout, dark mode, and
interactions look right.
