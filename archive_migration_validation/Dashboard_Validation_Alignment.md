# Dashboard Validation Alignment

Extends the existing dashboard (already showing XML validation as of
the prior milestone) so it stops implying "PASS" when DTD conformance
was never actually checked, and shows DTD compliance as its own,
separately-visible result. Purely additive — no page redesigned, no
existing field renamed or removed.

## What was wrong before

The Article Detail page, Home widget, and Analytics section all read
`FileValidationReport.result`/`PackageValidationReport.overall_result`
— a single merged PASS/WARNING/ERROR that, before real DTDs were
vendored, could only ever reflect well-formedness. Nothing distinguished
"actually DTD-valid" from "DTD not checked, so trivially passing." Now
that real DTDs are vendored and genuinely checked (see
`DTD_Compliance_Summary.md`), the corpus shows this gap concretely:
every package is well-formed, but article.xml/reviews.xml are not
DTD-valid in any of the 37 real articles — a fact the dashboard would
have hidden entirely under the old single-result model.

## Server (`dashboard/server/src/`)

- `types.ts` — `FileValidationReport` gained `well_formed_result`/
  `dtd_result`; `PackageValidationReport` gained `overall_dtd_result`;
  `ValidationIssue` gained `check` ("well-formed" | "dtd" | null).
  New `DtdResultBucket` type (`pass | warning | error | not_checked`).
- `SummaryStats`/`ValidationStats` both gained `dtd_counts` (a
  `DtdResultBucket`-keyed count), computed alongside the existing
  `validation_counts`/`overall_counts` in `dataStore.ts` — same
  aggregation pass, no new endpoint needed for `SummaryStats`; the
  existing `/analytics/validation` route now also returns `dtd_counts`.

## Web (`dashboard/web/src/`)

- `ValidationBadge` — now accepts `result: ValidationResultValue | null`
  and renders a distinct "Not Checked" badge for `null`, plus an
  optional `label` prop so a badge can read e.g. "DTD: Error" instead
  of a bare "Error".
- **Article Detail page**: the single "XML Validation" stat card is
  now two cards — "Well-formed XML" and "DTD Compliance" — each with
  its own badge. The "XML Validation" tab's per-file panel now shows
  two badges per file (`Well-formed: PASS`, `DTD: ERROR`) instead of
  one merged result, and each issue row is prefixed with which check
  produced it (`[dtd/error] No declaration for attribute...`).
- **Home page**: the existing "XML Validation" section is now labeled
  "well-formed + DTD, worst of both" (so it's clear what that number
  already meant), and a new "DTD Compliance (separate from
  well-formedness)" section shows Pass/Warning/Invalid/**Not Checked**
  counts on their own.
- **Analytics page**: the existing validation pie chart is now labeled
  the same way, and a new "DTD Compliance Only" pie chart (including a
  "not_checked" slice) sits right next to it, making the well-formed
  vs. DTD-valid split visually obvious rather than something a viewer
  has to infer.

## Verification

- `tsc -b --noEmit` (web) and `tsc -p tsconfig.json` (server): both
  clean.
- Confirmed live, through the already-running dashboard dev server,
  against batch `dtd-compliance-verify-3` (the real, post-fix corpus):
  - `/api/summary` → `dtd_counts: {pass: 0, warning: 0, error: 37, not_checked: 0}`
    (every article's article.xml/reviews.xml genuinely fails DTD
    conformance; the dashboard now says so instead of implying pass)
  - `/api/analytics/validation` → same `dtd_counts`, plus
    `common_issues` now shows real DTD messages
    ("No declaration for attribute data-type of element p",
    "No declaration for element string-name", ...) instead of nothing
  - `/api/articles/bcj-2025-3130` → `validation_report.overall_dtd_result: "error"`
    while `well_formed_result` is `"pass"` for every file — exactly
    the "well-formed but not DTD-valid" case this milestone asked the
    dashboard to make obvious.
