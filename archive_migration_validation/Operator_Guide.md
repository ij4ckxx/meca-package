# Operator Guide

## Start here: `Operator_Checklist.html`

Written once per batch, alongside every other batch report. Four
buckets, one line per article:

| Bucket | Meaning | Maps to |
|---|---|---|
| **Ready to Upload** | Package generated successfully | `certified` / `certified_with_warnings` / `certified_with_recovery` |
| **Ready for Manual Review** | Package generated, but a declared file is missing | `partial_certification` |
| **Needs Investigation** | No package — a defect in the engine itself | `engine_failure` |
| **Failed** | No package — the source data made safe generation impossible | `fatal_failure` |

This is a reporting-only view — it does not change where a package
physically lands (that's still `service/router.py`, unmodified).
"Needs Investigation" and "Failed" both land in the same `failed/`
folder; this checklist just tells you which of the two you're looking
at before you open anything.

## Before uploading any single package

Open its **Migration Audit Report**
(`MECA_<ArticleID>_Migration_Audit_Report.html`, or from the dashboard's
Article Detail page → "Migration Audit Report" button, or the Migration
Audit page's "Open Migration Audit Report" link). It answers, in one
page:

- What's the package/certification status and confidence?
- Which Business Rules fired, and how (Applied / Warning / Recovery /
  Failed)?
- Which Recovery Rules applied, and why (with a plain-English reason)?
- What warnings, source problems, and DTD problems remain?
- Which files were generated, and which are missing?
- Who/what produced it (engine version, config checksum, DTD/Business
  Rule/Recovery Rule versions) — everything needed to reproduce it
  later.

## For a failed article ("Needs Investigation" or "Failed")

Open its **Certification Report** (`MECA_<ArticleID>_Certification_Report.html`)
first — it now shows a **Failure Reason** section with the actual,
specific cause (e.g. "No source XML found for ... under ..."), not just
the generic per-status sentence. The Dashboard's Article Detail page
shows the same message under "Failure" instead of a raw internal-object
dump.

## Corpus-level triage

Open **`Batch_Audit_Report.html`** for the whole batch: totals by
status, Business Rule / Recovery Rule / DTD statistics, top source
problems, top manual-review reasons, and a journal-by-journal
comparison — all reused directly from the existing intelligence reports
this engine already produced, laid out on one page.

## What to do with a "Remaining" finding

- **Remaining Source Problems** — the publisher's own data is
  incomplete or inconsistent. The engine never invents a fix; these are
  flagged for manual review, not automatically repaired.
- **Remaining DTD Problems** — the file is well-formed XML but not
  fully DTD-conformant. Each finding is already classified (Source Data
  Issue / Business Rule Candidate / Recovery Rule Candidate /
  Validation Only) — see the DTD-compliance milestone's own
  documentation for what each category means and why it wasn't
  auto-fixed.
- A **blank Input/Output XML Location** in the Rule Traceability table
  means the engine doesn't track element-level location for that
  finding today — it is not an error in the report.

## Running a large batch over hours/days

The Dashboard's article list (`conversion_reports.json`) refreshes every
25 completed articles during the run, not only once it finishes — you
can watch a large batch populate progressively instead of seeing an
empty list until it's done.

**Restarting a subset** (re-running the same `--batch-id` with a
narrower `--article-ids`, e.g. just the articles that failed or need
manual review) is safe: every other article's record is preserved, not
overwritten — the Dashboard/aggregate reports always reflect the union
of everything ever processed under that batch id, not just the most
recent run.

A confidence score of 100 does **not** mean a package is DTD-clean —
confidence is an advisory signal derived from warnings/recoveries only,
independent of DTD/validation results. Always check the DTD Result
separately (Migration Audit Report, or the Article Detail page's own
DTD badge) even for a high-confidence article.

## Reproducibility

Every Migration Audit Report records the exact engine version, Business
Rule Book version, Recovery Rule version, DTD version, and a
configuration checksum. Two packages with identical checksums and
engine version were built under identical rules — if you need to
reproduce a package's exact behavior later, this is the record to
check against.
