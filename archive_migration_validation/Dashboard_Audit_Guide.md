# Dashboard Audit Guide

## New page: Migration Audit

Sidebar → **Migration Audit** (`/migration-audit`). Same table/filter
layout as the existing Articles page, extended with filters for:

- Journal, Status, Confidence (already existed on Articles)
- Business Rule, Recovery Rule, Warning (already existed server-side;
  now exposed in this page's UI)
- **Validation Result** and **DTD Result** (new — `pass` / `warning` /
  `error`, plus `not_checked` for DTD)

Selecting **"Open Migration Audit Report →"** on any row opens that
article's complete `Migration_Audit_Report.html` in a new tab.

## Article Detail page — what's new

- Two new download buttons: **Migration Audit Report** and
  **migration-audit.json**, alongside the existing MECA ZIP /
  Certification Report / Validation Report / conversion-report.json
  buttons (all six now downloadable from one place, per this
  milestone's requirement).
- A new **"Migration Audit"** tab showing the package's Reproducibility
  record (engine version, config checksum, DTD/Business Rule/Recovery
  Rule versions, generation timestamp, Python version, OS) and a link
  to the full report.

## Filtering, technically

`GET /api/articles` already supported `journal`/`status`/`confidence`/
`recovery_rule`/`business_rule`/`warning`. Two params were added:

- `validation=pass|warning|error` — filters on
  `validation_report.overall_result`.
- `dtd_result=pass|warning|error|not_checked` — filters on
  `validation_report.overall_dtd_result` (`not_checked` matches a
  `null` value, i.e. no DTD result recorded).

No new endpoint was created for this — the existing route's filter
logic was extended in place.

## Downloads, all in one place

From an Article Detail page's button row:

| Button | File |
|---|---|
| MECA ZIP | `MECA_<id>.zip` |
| raw/article/transfer/manifest/reviews.xml | extracted from the ZIP |
| Certification Report | `MECA_<id>_Certification_Report.html` |
| Validation Report | `MECA_<id>_Validation_Report.html` |
| Migration Audit Report | `MECA_<id>_Migration_Audit_Report.html` |
| conversion-report.json | embedded in the ZIP |
| migration-audit.json | written alongside the package |

Batch-level `Batch_Audit_Report.html` and `Operator_Checklist.html` are
downloadable the same way every other batch report already is, via the
existing `/api/reports/:filename` route (no new route needed).

## What was not changed

No existing page was redesigned, no existing route's response shape
changed for existing callers (both new query params are optional), and
no existing button/tab was removed or renamed.
