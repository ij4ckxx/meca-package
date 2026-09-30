# Dashboard Validation Integration — Milestone 4

Purely additive extension of the existing Express+TS / React+TS
dashboard. No page was redesigned, no existing route/type/component
was removed or renamed — only new fields, one new route family, one
new tab, and small new sections on Home/Analytics.

## Data flow (nothing new to compute)

`validation_report` was already embedded in every article's
`conversion-report.json` by Milestone 2, and `processing_service.py`
already writes every article's report into the batch's
`conversion_reports.json` — the exact file `dataStore.ts` already
reads. No engine-side change was needed; the dashboard only had to stop
ignoring a field that was already there.

## Server (`dashboard/server/src/`)

- `types.ts` — added `ValidationResultValue`, `ValidationIssue`,
  `FileValidationReport`, `PackageValidationReport`, `ValidationStats`
  types; added `validation_report` to `ConversionReportRecord`,
  `validationHtmlFile` to `ArticleLocation`, `has_validation_report` to
  `ArticleDetail`, `validation_counts` to `SummaryStats`.
- `dataStore.ts` — `scanArticleLocations()` now also finds
  `*_Validation_Report.html`; `getArticle()`/`getArticleFile()` extended
  to serve it (third `"validation"` kind, alongside the existing
  `"zip"`/`"certification"`); `getSummary()` now tallies
  `validation_counts`; new `getValidationStats()` aggregates
  pass/warning/error totals, error/warning counts, DTD-not-vendored file
  count, and the 10 most common issue messages across the batch.
- `routes.ts` — new `GET /articles/:id/download/validation`,
  `GET /articles/:id/view/validation`, `GET /analytics/validation`,
  mirroring the existing certification routes exactly.

## Web (`dashboard/web/src/`)

- `types.ts` / `api.ts` — mirrored the same new types/fields;
  `validationReportDownloadUrl`/`validationReportViewUrl`/
  `getValidationStats` added.
- `components/ValidationBadge.tsx` (new, small) — pass/warning/error
  badge, same visual pattern as `StatusBadge`.
- `pages/ArticleDetailPage.tsx` — new "XML Validation" stat card
  (result badge + error/warning counts), new "Validation Report"
  download button (disabled when unavailable, matching the
  Certification Report button's pattern exactly), new "XML Validation"
  tab showing all 4 files' PASS/WARNING/ERROR, DTD name/availability,
  and every issue (severity, message, line, xpath), plus a link to the
  full standalone HTML report.
- `pages/HomePage.tsx` — new "XML Validation" summary section (Pass /
  Warning / Error counts with percentages), same `StatCard`/`stat-grid`
  pattern as every other Home section.
- `pages/AnalyticsPage.tsx` — new "XML Validation Results" section
  (total errors/warnings, DTD-not-vendored count, a pass/warning/error
  pie chart) and "Most Common Validation Issues" bar chart, following
  the exact chart patterns already used for Status Distribution and
  Warning Frequency.

## Verification

- `tsc -b --noEmit` (web) and `tsc -p tsconfig.json` (server): both
  clean.
- Hit every new endpoint against the real `milestone2-verify` batch
  (37 articles) through the already-running dashboard dev server
  (hot-reloaded automatically):
  - `/api/summary` → `validation_counts: {pass: 37, warning: 0, error: 0}`
  - `/api/analytics/validation` → `dtd_not_vendored_count: 148`
    (37 articles × 4 files — correct, since no DTDs are vendored)
  - `/api/articles/bcj-2025-3130` → `has_validation_report: true`,
    `validation_report.overall_result: "pass"`
  - `/articles/:id/view/validation` and `/download/validation` → both
    return the standalone HTML report with `200 OK`.
- Verified through the Vite dev server's proxy as well (`localhost:5173`
  → `localhost:4000`), confirming the frontend receives the same data
  a browser session would.
