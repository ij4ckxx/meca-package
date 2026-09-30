# Dashboard Implementation Summary

## What was built

A read-only operator dashboard, per the org's stated JS/TS default
stack: a Node/Express + TypeScript API (`dashboard/server/`) and a React
+ TypeScript frontend (`dashboard/web/`), living as a new sibling app at
`meca-package/dashboard/` — no changes to `meca-engine/`.

The dashboard reads exactly what the engine already produces:
`conversion_reports.json`, `dashboard_intelligence.json`, and the
`uploaded/`/`manual_review/`/`failed/` folders `OutputRouter` (Phase 3)
already routes packages into. No conversion logic, no new report
computation — the dashboard only reads and presents.

## One terminology clarification worth flagging

`dashboard_intelligence.json`'s own `manual_review` field (from Milestone
14's intelligence layer) is a broader analytical concept — it lists every
article that isn't perfectly clean-`CERTIFIED` (33 of 37 in the current
corpus). That is **not** the same thing as Phase 3's `manual_review/`
output folder (only 4 articles — the `PARTIAL_CERTIFICATION` ones). The
dashboard's "Manual Review" page uses the real routing outcome (which
folder an article actually landed in), not that intelligence field, since
that's what "needs a human to act on it" actually means operationally.

## Pages delivered

Home, Per Journal, Articles (list), Article Detail (tabs: Business
Rules / Recovery Rules / Warnings / Missing Files / Generated Files /
Certification Report, plus 3 downloads), Manual Review, Analytics
(Recovery Rule Effectiveness + Warning Analytics) — matching every
section in the requested wireframe.

## Verification performed

- `tsc --noEmit` (server) and `tsc -b --noEmit` (web) — both clean.
- Production builds succeed for both (`vite build`, `tsc`).
- `npm audit` — 0 vulnerabilities (upgraded `react-router-dom` v6→v7 after
  finding 2 moderate CVEs in v6; the v7 migration was a no-op for the
  basic APIs this app uses).
- Every API endpoint hit directly against the real 37-article corpus and
  checked against the source JSON: summary counts, per-journal stats,
  article list/detail, manual-review queue (verified it lists exactly
  the 4 real `manual_review/` articles), recovery-rule and warning
  analytics (numbers match the corpus's own generated reports, e.g.
  RR-004: 189 occurrences).
- Full frontend+backend stack run together locally; confirmed the Vite
  dev server proxies `/api/*` to the Express server correctly.
- Synthetic-failure test: temporarily added one `engine_failure` article
  to `failed/` and `conversion_reports.json` to confirm the dashboard
  correctly shows `category: failed`, disables the ZIP download (none
  exists), and still serves its Certification Report — since the real
  corpus currently has zero failures to check this against live. Removed
  afterward; real data confirmed restored to 37 articles.

## Not built (explicitly out of scope for this phase)

"Upload to SFTP" button — no real SFTP provider exists yet. Documented
in `dashboard/README.md` as a one-button addition once it does.
