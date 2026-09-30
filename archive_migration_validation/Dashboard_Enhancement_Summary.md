# Dashboard Enhancement Summary

## What was implemented

All 16 sections, as dashboard-only extensions. No engine, PackageBuilder,
generator, Business Rule, Recovery Rule, Processing Service, Provider,
Reporting, or Intelligence code was touched — the dashboard still reads
exactly what those already produce.

**Design**: full visual rework per your "latest design template" request
— CSS custom properties driving a light/dark theme (toggle in the
sidebar, persisted locally), `lucide-react` icons throughout, refined
typography/spacing/cards, sticky table headers, `sonner` toast
notifications on every action, consistent loading/empty/error states.

**New pages**: Batch History (per-batch stats + report downloads), Batch
Comparison (diff two batches' status/confidence/journal/recovery/warning/duration),
Journal Health (dedicated, with a batch-over-batch confidence trend
arrow).

**Enhanced pages**: Home (percentages, journal distribution, latest
batch, processing duration, avg. time/article, recovery/warning counts,
business rule failures, top recovery rule usage), Article Detail
(Business Rule Timeline, Recovery Timeline, package size, DOI note, XML
downloads for all 5 generated documents, manual review reason), Manual
Review (operator notes + Mark Reviewed/Accepted/Rejected, export,
restart-all), Analytics (real charts via `recharts` for every requested
dimension, top missing files, cross-batch processing-time/recovery/warning
trends), Logs (search, severity filter, collapse, download), Articles
(pagination, warning filter, export), Configuration (client-side
validation hints alongside the existing server-side schema validation).

**Backend additions** (all new Node code, zero Python changes): batch
summary stats, a report-file download endpoint (allowlisted), XML
extraction directly from the already-built zip (`adm-zip`), package
size, business-rule and missing-file analytics endpoints, manual-review
notes persisted as local JSON per batch.

## Deviations / scope calibration

- **Pagination instead of virtualization.** The current corpus is 37
  articles; a virtualized table (`react-window`) would be solving a
  problem that doesn't exist yet. Pagination + memoized filtering is the
  proportionate choice — documented, not hidden.
- **Excel export ships as CSV, not `.xlsx`.** `xlsx` (SheetJS) has an
  unpatched high-severity CVE (prototype pollution / ReDoS); its
  replacement `exceljs` pulls in a vulnerable `uuid`. CSV opens natively
  and correctly in Excel, so "Excel export" is CSV — no dependency with
  a known, unfixed vulnerability shipped for a cosmetic difference.
- **A "Date" filter wasn't added separately from the batch selector.**
  Articles don't carry their own per-article date — only the batch
  they're part of does. The batch selector already is the date filter.
- **DOI is still not searchable/displayable**, same reason as before:
  not exposed by `ConversionReport` (Reporting), out of scope to add.
- **Two real, non-obvious filter bugs found and fixed during
  verification**: the warning filter and global search only checked
  `ConversionReport.warnings`, which is empty for this entire corpus —
  every actual finding here is classified as a `recovery`. Both now
  check `warnings` and `recoveries` together, matching how the engine's
  own intelligence layer already defines "warnings" for its Warning
  Analytics table. Same fix applied to the new per-journal "most common
  warning" field.

## Confirmation: existing engine behavior is unchanged

Two full real batches were run through the dashboard during
verification (the full 37-article corpus, and a 4-article
restart-manual-review run) — both used the unmodified
`scripts/archive_migration_batch.py` and produced the exact package/report
output every prior phase already verified. See `Dashboard_Verification.md`.
