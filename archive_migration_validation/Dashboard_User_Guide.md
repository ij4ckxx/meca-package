# Dashboard User Guide

## Running it

```bash
cd dashboard
npm run dev   # starts API (4000) + UI (5173) together
```
Open `http://localhost:5173`. Toggle light/dark mode from the sidebar.

## Sidebar

**Batch selector** — "Latest" or any prior run; every page reflects the
selection. **Nav**: Control Center, Home, Batch History, Batch
Comparison, Per Journal, Journal Health, Articles, Manual Review,
Analytics, Logs, Configuration.

## Control Center

Start Migration, Pause, Resume, Stop After Current Article, Cancel
Batch, Restart Failed/Manual-Review Articles — each gives a toast
confirmation. Live Job Status (polled every ~3s): job state, current
article, remaining, elapsed, ETA, speed, and a live "routed so far"
breakdown that fills in as the run progresses.

## Home

Total packages and every status count with percentages, processing
duration and average time per article, confidence distribution, journal
distribution, recovery/warning counts, business rule failures, and top
recovery rule usage — all for the selected batch.

## Batch History

Every run: batch ID, date, time, package count, success/recovery/manual-review/failed
counts, duration. Click the eye icon to view that batch everywhere else.
Below the table: direct downloads for Migration Summary, Recovery
Analytics, Business Rule Statistics, Journal Health Report, audit/manual-review
CSVs, and the dashboard JSON.

## Batch Comparison

Pick batch A and B; see status, confidence, journal, recovery-rule, and
warning differences, plus each batch's processing duration, side by
side.

## Per Journal / Journal Health

Per Journal: article count, recovery rate, common recovery rule,
warnings, average confidence. Journal Health (dedicated): the same
data plus a trend arrow (versus the immediately preceding batch) and
each journal's most common warning.

## Articles

Search (article id, journal, status, business/recovery rule, warning
code — not DOI, see Known Limitations) plus journal/status/confidence
filters, paginated (15 per page), exportable as CSV/JSON/PDF.

## Article Detail

Certification decision, confidence, warnings+recoveries, package size,
and: **Summary** (DOI note, category, manual review reason if
applicable, recovery rules applied), **Business Rule Timeline** (every
rule grouped by number: passed / warning / recovered), **Recovery
Timeline** (rule, reason, confidence, affected file, business rule
impacted), **Warnings**, **Missing Files**, **Generated Files**,
**Certification Report** (rendered inline). Downloads: MECA ZIP, all 5
generated XML documents individually (raw/article/transfer/manifest/reviews,
extracted directly from the zip), Certification Report,
`conversion-report.json` — each only shown if actually available.

## Manual Review Workspace

Every manual-review article: reason, confidence, a notes textarea, and
Mark Reviewed / Accepted / Rejected buttons. Notes and status are
stored as local JSON per batch — no database. Export the whole list;
"Restart All" re-runs every visible article as a new batch.

## Analytics

Success %/Manual Review %, average/median confidence, and charts for
Status Distribution, Confidence Distribution, Recovery Rule Frequency,
Warning Frequency, Business Rule Frequency, Top Missing Files, and
(across your batch history) Processing Time and Recovery/Warning
trends. All read from the engine's existing intelligence output.

## Logs

Live tail of the current/most recent run, with search, severity filter
(error/warning/info), collapse, and download.

## Configuration

Edit Input/Output Provider, Dashboard folders, Worker Count, Retry
settings, Logging level, and Processing options. Client-side hints
catch obvious mistakes immediately; every save is still validated
against the engine's own schema before being written, with the
schema's own error shown on rejection.

## Known limitations

See `Known_Limitations.md` for the full list (unchanged from Phase 5,
plus: Excel export is CSV, not `.xlsx`, due to unpatched CVEs in the
available libraries; no per-article date field, so filtering by date
means switching batches; virtualized tables weren't added since the
corpus is only 37 rows — pagination covers it).
